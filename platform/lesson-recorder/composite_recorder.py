"""Records one LiveKit room to a SINGLE composited MP4 (one file per lesson)
and uploads it to Backblaze -- the "watch the whole lesson back" view, not a
per-participant file list.

Layout is screenshare-first: whenever someone is sharing their screen it fills
the frame with the participant cameras as a thumbnail strip along the bottom;
with no screenshare the cameras fall back to an even grid. The canvas is a
fixed 1280x720 so encoding cost is constant no matter how many cameras are on
(one 720p/15fps H.264 encode per lesson), unlike the per-participant recorder
whose cost scaled with the number of published camera tracks.

Video is composited in-process (Pillow draws each tick's canvas) and piped to a
single ffmpeg encoder; audio is captured per track to cheap AAC files and mixed
together (ffmpeg amix) into the final mux at the end -- realtime PCM mixing in
Python is fiddly and error-prone, a one-shot amix at finalize is not.

Same CLI/`run()` contract as recorder_bot.py so watcher.py can spawn either one
based on RECORDING_MODE.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

from livekit import rtc
from minio import Minio
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("composite-recorder")

# Same lifecycle windows as the per-participant recorder.
_EMPTY_ROOM_GRACE_SECONDS = 10
_INITIAL_JOIN_TIMEOUT_SECONDS = 15 * 60

# Output canvas. Fixed size => constant encode cost regardless of participants.
CANVAS_W = 1280
CANVAS_H = 720
FPS = 15
# Bottom strip reserved for camera thumbnails while a screenshare is on screen.
THUMB_STRIP_H = 132
THUMB_W = 208
THUMB_H = 117
THUMB_GAP = 10
MAX_THUMBS = 6  # 6*208 + 5*10 = 1298 -> we center and clip to canvas width
BLACK = (0, 0, 0)


def _paste_contain(canvas: Image.Image, img: Image.Image, box: tuple[int, int, int, int]) -> None:
    """Scale img to fit inside box (x, y, w, h) keeping aspect, centered."""
    x, y, w, h = box
    if w <= 0 or h <= 0 or img.width == 0 or img.height == 0:
        return
    scale = min(w / img.width, h / img.height)
    nw, nh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    resized = img.resize((nw, nh), Image.BILINEAR)
    canvas.paste(resized, (x + (w - nw) // 2, y + (h - nh) // 2))


class VideoTrackState:
    """Holds the most recent frame for one video track as raw RGBA bytes.

    We keep only the latest frame (not a queue) and convert it to a Pillow
    image lazily at composite time -- so conversion happens at the 15fps canvas
    rate, not at each track's native (often 30fps) delivery rate.
    """

    def __init__(self, is_screenshare: bool) -> None:
        self.is_screenshare = is_screenshare
        self._latest: tuple[int, int, bytes] | None = None
        self._task: asyncio.Task | None = None

    def start(self, track: rtc.RemoteVideoTrack) -> None:
        self._task = asyncio.create_task(self._read(track))

    async def _read(self, track: rtc.RemoteVideoTrack) -> None:
        stream = rtc.VideoStream(track)
        try:
            async for event in stream:
                frame = event.frame.convert(rtc.VideoBufferType.RGBA)
                self._latest = (frame.width, frame.height, bytes(frame.data))
        except Exception:
            log.exception("video track reader crashed")
        finally:
            await stream.aclose()

    def image(self) -> Image.Image | None:
        latest = self._latest
        if latest is None:
            return None
        w, h, data = latest
        return Image.frombuffer("RGBA", (w, h), data, "raw", "RGBA", 0, 1).convert("RGB")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass


class AudioCapture:
    """One cheap AAC file per audio track; mixed together at finalize."""

    def __init__(self, work_dir: str, sid: str, elapsed_ms) -> None:
        self.path = os.path.join(work_dir, f"audio-{sid}.m4a")
        self.has_data = False
        # Milliseconds between the start of the composited video and this
        # track's first audio frame. The recorder joins before anyone else, so
        # unless that gap is replayed as silence at mux time every late
        # joiner's voice slides to t=0 and runs ahead of the picture.
        self.offset_ms = 0
        self._elapsed_ms = elapsed_ms
        self._proc: subprocess.Popen | None = None
        self._task: asyncio.Task | None = None

    def start(self, track: rtc.RemoteAudioTrack) -> None:
        self._task = asyncio.create_task(self._read(track))

    async def _read(self, track: rtc.RemoteAudioTrack) -> None:
        stream = rtc.AudioStream(track)
        try:
            async for event in stream:
                frame = event.frame
                if self._proc is None:
                    self.offset_ms = self._elapsed_ms()
                    self._proc = subprocess.Popen(
                        [
                            "ffmpeg", "-y", "-f", "s16le",
                            "-ar", str(frame.sample_rate), "-ac", str(frame.num_channels),
                            "-use_wallclock_as_timestamps", "1", "-i", "-",
                            "-c:a", "aac", self.path,
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.has_data = True
                try:
                    self._proc.stdin.write(bytes(frame.data))
                except (BrokenPipeError, OSError):
                    break
        except Exception:
            log.exception("audio track reader crashed")
        finally:
            await stream.aclose()

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        if self._proc is not None:
            try:
                self._proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            try:
                self._proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self._proc.kill()


class CompositeRecorder:
    def __init__(self, work_dir: str) -> None:
        self.work_dir = work_dir
        self.video_path = os.path.join(work_dir, "composite.video.mp4")
        self._videos: dict[str, VideoTrackState] = {}
        self._audios: dict[str, AudioCapture] = {}
        self._encoder: subprocess.Popen | None = None
        self._compositor_task: asyncio.Task | None = None
        self._t0: float | None = None
        self._running = False

    # ---- track wiring ----
    def add_video(self, sid: str, track: rtc.RemoteVideoTrack, is_screenshare: bool) -> None:
        state = VideoTrackState(is_screenshare)
        state.start(track)
        self._videos[sid] = state
        log.info("video track added sid=%s screenshare=%s (%d total)", sid, is_screenshare, len(self._videos))

    def add_audio(self, sid: str, track: rtc.RemoteAudioTrack) -> None:
        cap = AudioCapture(self.work_dir, sid, self._elapsed_ms)
        cap.start(track)
        self._audios[sid] = cap
        log.info("audio track added sid=%s (%d total)", sid, len(self._audios))

    def remove_track(self, sid: str) -> None:
        vs = self._videos.pop(sid, None)
        if vs is not None:
            asyncio.create_task(vs.stop())
            log.info("video track removed sid=%s (%d left)", sid, len(self._videos))

    # ---- compositing ----
    def start(self) -> None:
        self._encoder = subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{CANVAS_W}x{CANVAS_H}", "-framerate", str(FPS), "-i", "-",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-g", str(FPS * 2),
                self.video_path,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._t0 = time.monotonic()
        self._running = True
        self._compositor_task = asyncio.create_task(self._composite_loop())

    def _elapsed_ms(self) -> int:
        """Milliseconds since the video encoder started; 0 before it has."""
        if self._t0 is None:
            return 0
        return max(0, int((time.monotonic() - self._t0) * 1000))

    def _build_canvas(self, videos: list[VideoTrackState]) -> Image.Image:
        canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
        screenshares = [v for v in videos if v.is_screenshare]
        cameras = [v for v in videos if not v.is_screenshare]

        share_img = None
        for v in screenshares:
            share_img = v.image()
            if share_img is not None:
                break

        cam_imgs = [img for img in (c.image() for c in cameras) if img is not None]

        if share_img is not None:
            main_h = CANVAS_H - (THUMB_STRIP_H if cam_imgs else 0)
            _paste_contain(canvas, share_img, (0, 0, CANVAS_W, main_h))
            if cam_imgs:
                n = min(len(cam_imgs), MAX_THUMBS)
                total_w = n * THUMB_W + (n - 1) * THUMB_GAP
                start_x = max(0, (CANVAS_W - total_w) // 2)
                y = main_h + (THUMB_STRIP_H - THUMB_H) // 2
                x = start_x
                for img in cam_imgs[:n]:
                    _paste_contain(canvas, img, (x, y, THUMB_W, THUMB_H))
                    x += THUMB_W + THUMB_GAP
        elif cam_imgs:
            n = len(cam_imgs)
            cols = math.ceil(math.sqrt(n))
            rows = math.ceil(n / cols)
            cell_w = CANVAS_W // cols
            cell_h = CANVAS_H // rows
            for i, img in enumerate(cam_imgs):
                r, c = divmod(i, cols)
                _paste_contain(canvas, img, (c * cell_w, r * cell_h, cell_w, cell_h))
        # else: nothing published yet -> black frame (keeps the encoder alive)
        return canvas

    def _render_and_write(self, videos: list[VideoTrackState]) -> None:
        canvas = self._build_canvas(videos)
        if self._encoder and self._encoder.stdin:
            self._encoder.stdin.write(canvas.tobytes())

    async def _composite_loop(self) -> None:
        loop = asyncio.get_event_loop()
        frame_interval = 1.0 / FPS
        next_t = loop.time()
        while self._running:
            try:
                # Snapshot the tracks here, on the event-loop thread, so the
                # dict can't change mid-iteration; then resize and push the
                # 2.7 MB frame off-thread -- a full ffmpeg pipe would
                # otherwise stall this loop and every track reader with it.
                await loop.run_in_executor(
                    None, self._render_and_write, list(self._videos.values())
                )
            except (BrokenPipeError, OSError):
                break
            except Exception:
                log.exception("composite tick failed")
            next_t += frame_interval
            delay = next_t - loop.time()
            if delay < -1.0:  # we're badly behind; resync instead of spiraling
                next_t = loop.time()
                delay = 0
            await asyncio.sleep(max(0, delay))

    async def finalize(self, room_name: str) -> str | None:
        self._running = False
        if self._compositor_task:
            try:
                await self._compositor_task
            except Exception:
                pass
        for vs in list(self._videos.values()):
            await vs.stop()
        if self._encoder is not None:
            try:
                self._encoder.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            try:
                self._encoder.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self._encoder.kill()

        for cap in list(self._audios.values()):
            await cap.stop()

        if not os.path.exists(self.video_path) or os.path.getsize(self.video_path) == 0:
            log.warning("no composited video produced")
            return None

        audio_tracks = [
            (c.path, c.offset_ms) for c in self._audios.values()
            if c.has_data and os.path.exists(c.path) and os.path.getsize(c.path) > 0
        ]
        out_path = os.path.join(self.work_dir, "lesson.mp4")

        if not audio_tracks:
            # video only
            r = subprocess.run(["ffmpeg", "-y", "-i", self.video_path, "-c", "copy", out_path], capture_output=True)
            return out_path if r.returncode == 0 else self.video_path

        # Pad each track back out to where it actually started relative to the
        # video, then mix. No -shortest: someone who leaves early ends their
        # audio early, and -shortest would cut the lesson video off there too.
        cmd = ["ffmpeg", "-y", "-i", self.video_path]
        for path, _ in audio_tracks:
            cmd += ["-i", path]
        stages = [
            f"[{i + 1}:a]adelay={offset}:all=1[a{i}]"
            for i, (_, offset) in enumerate(audio_tracks)
        ]
        labels = "".join(f"[a{i}]" for i in range(len(audio_tracks)))
        if len(audio_tracks) == 1:
            stages.append(f"{labels}anull[a]")
        else:
            stages.append(f"{labels}amix=inputs={len(audio_tracks)}:duration=longest:normalize=0[a]")
        cmd += [
            "-filter_complex", ";".join(stages),
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", out_path,
        ]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            log.warning("mux failed: %s", r.stderr.decode(errors="replace")[-500:])
            return self.video_path
        return out_path


def _is_screenshare(publication) -> bool:
    try:
        return publication.source == rtc.TrackSource.SOURCE_SCREENSHARE
    except Exception:
        return False


async def run(room_name: str, token: str, url: str, s3_settings: dict, max_seconds: int = 4 * 3600) -> None:
    work_dir = tempfile.mkdtemp(prefix=f"rec-{room_name}-")
    recorder = CompositeRecorder(work_dir)
    room = rtc.Room()
    empty_since: float | None = None

    def _wire(track, publication, participant) -> None:
        if track.kind == rtc.TrackKind.KIND_VIDEO:
            recorder.add_video(track.sid, track, _is_screenshare(publication))
        elif track.kind == rtc.TrackKind.KIND_AUDIO:
            recorder.add_audio(track.sid, track)

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        _wire(track, publication, participant)

    @room.on("track_unsubscribed")
    def on_track_unsubscribed(track, publication, participant):
        recorder.remove_track(track.sid)

    log.info("connecting to room %s", room_name)
    await room.connect(url, token, options=rtc.RoomOptions(auto_subscribe=True))
    recorder.start()
    log.info("connected, %d participants already present", len(room.remote_participants))
    for p in room.remote_participants.values():
        for pub in p.track_publications.values():
            if pub.track is not None:
                _wire(pub.track, pub, p)

    ever_had_participant = len(room.remote_participants) > 0
    loop = asyncio.get_event_loop()
    start_time = loop.time()
    while True:
        await asyncio.sleep(3)
        now = loop.time()
        if len(room.remote_participants) > 0:
            ever_had_participant = True
            empty_since = None
        elif not ever_had_participant:
            if now - start_time >= _INITIAL_JOIN_TIMEOUT_SECONDS:
                log.info("nobody joined %s within %ds, giving up", room_name, _INITIAL_JOIN_TIMEOUT_SECONDS)
                break
        else:
            empty_since = empty_since or now
            if now - empty_since >= _EMPTY_ROOM_GRACE_SECONDS:
                break
        if now - start_time >= max_seconds:
            log.warning("hit the %ds safety cap for %s, stopping regardless of room state", max_seconds, room_name)
            break

    log.info("room empty, finalizing composite recording")
    await room.disconnect()

    path = await recorder.finalize(room_name)
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        log.warning("nothing recorded, nothing to upload")
        shutil.rmtree(work_dir, ignore_errors=True)
        return

    client = Minio(
        s3_settings["endpoint"], access_key=s3_settings["access_key"],
        secret_key=s3_settings["secret_key"], secure=True, region="auto",
    )
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    object_name = f"{room_name}/{timestamp}.mp4"
    client.fput_object(s3_settings["bucket"], object_name, path)
    log.info("uploaded composite (%d bytes) -> %s", os.path.getsize(path), object_name)

    shutil.rmtree(work_dir, ignore_errors=True)
    log.info("done")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--room", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--s3-endpoint", required=True)
    parser.add_argument("--s3-access-key", required=True)
    parser.add_argument("--s3-secret-key", required=True)
    parser.add_argument("--s3-bucket", required=True)
    parser.add_argument("--max-seconds", type=int, default=4 * 3600)
    args = parser.parse_args()

    s3_settings = {
        "endpoint": args.s3_endpoint,
        "access_key": args.s3_access_key,
        "secret_key": args.s3_secret_key,
        "bucket": args.s3_bucket,
    }
    asyncio.run(run(args.room, args.token, args.url, s3_settings, args.max_seconds))


if __name__ == "__main__":
    sys.exit(main())
