"""Records one LiveKit room to a SINGLE composited MP4 (one file per lesson)
and uploads it to Backblaze -- the "watch the whole lesson back" view, not a
per-participant file list.

Layout is screenshare-first: whenever someone is sharing their screen it fills
the frame with the participant cameras as a thumbnail strip along the bottom;
with no screenshare the cameras fall back to an even grid. Every participant
currently in the room gets exactly one tile either way -- a live camera image
if they've published one, otherwise a name/initials placeholder, the same way
the frontend's LiveKit <VideoConference/> shows a labelled tile for a
camera-off participant instead of nothing. Without this, a lesson where
nobody ever turns a camera on (routine here -- audio + a shared screen is the
normal way a lesson runs) composited to a plain black video, which looked
nothing like what anyone on the call actually saw. Tiles are ordered teacher
first, then students, matching how a lesson is framed live. The canvas is a
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
import functools
import logging
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from livekit import rtc
from minio import Minio
from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("composite-recorder")

# The recording window follows the lesson's own clock (watcher.py starts
# this process around scheduled_start and caps it at scheduled_end plus a
# buffer via --max-seconds), NOT participant presence -- a lesson briefly
# going empty (someone's tab reloads, a wifi blip) no longer ends the
# recording, it just rides out the rest of the clock window with a black/
# silent gap in the middle. Only a genuine "nobody ever showed up" case
# still cuts things short, via this timeout.
_INITIAL_JOIN_TIMEOUT_SECONDS = 45 * 60
# Process exit code signalling "nobody ever joined, gave up" -- watcher.py
# checks for exactly this to mark the lesson missed right away instead of
# waiting for it to read as missed on its own once scheduled_end passes.
# Must match recorder_bot.py's own copy of this constant.
NO_SHOW_EXIT_CODE = 2

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


# "Camera off" tile: dark background, initials in a circle, name underneath --
# built at a nominal 16:9 so it drops into _paste_contain like a real camera
# frame and scales cleanly into whatever cell size the layout gives it.
_PLACEHOLDER_W, _PLACEHOLDER_H = 640, 360
_PLACEHOLDER_BG = (32, 34, 40)
_PLACEHOLDER_AVATAR = (71, 105, 245)
_PLACEHOLDER_TEXT = (235, 236, 240)
# Installed via the Dockerfile (fonts-dejavu-core) specifically for Cyrillic
# coverage -- participant names here are routinely Cyrillic, and Pillow's own
# bundled default font can't be relied on for that. Falls back to the default
# font so this still runs (Latin-only) outside the container, e.g. local dev.
_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


@functools.lru_cache(maxsize=8)
def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default(size=size)


def _initials(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, cx: int, cy: int, font) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (right - left) / 2 - left, cy - (bottom - top) / 2 - top), text, font=font, fill=_PLACEHOLDER_TEXT)


@functools.lru_cache(maxsize=64)
def _placeholder_image(name: str) -> Image.Image:
    """A tile for a participant with no live camera track -- so the recording
    still shows everyone who was actually in the lesson, the way the
    frontend's own call UI does, instead of that participant simply not
    existing on the canvas.

    Cached per name: this is drawn from scratch (font rasterisation and all)
    the first time, then reused for every composite tick a camera-off
    participant is on screen -- redoing that 15 times a second per such
    participant would undercut the whole point of the earlier fix to how
    much work each tick does."""
    img = Image.new("RGB", (_PLACEHOLDER_W, _PLACEHOLDER_H), _PLACEHOLDER_BG)
    draw = ImageDraw.Draw(img)
    radius = 68
    cx, cy = _PLACEHOLDER_W // 2, _PLACEHOLDER_H // 2 - 24
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=_PLACEHOLDER_AVATAR)
    _draw_centered(draw, _initials(name), cx, cy, _load_font(54))
    label = name if len(name) <= 24 else name[:23] + "…"
    _draw_centered(draw, label, _PLACEHOLDER_W // 2, cy + radius + 40, _load_font(26))
    return img


class VideoTrackState:
    """Holds the most recent frame for one video track, undecoded.

    We keep only the latest frame (not a queue) and defer BOTH the RGBA
    colour-space convert and the Pillow wrap to composite time (image()),
    so that work happens at the 15fps canvas rate, not at each track's
    native (often 30fps, sometimes higher for a screenshare) delivery rate.
    Previously the RGBA convert ran in _read() on every arriving frame --
    twice the work this state ever needed, and the dominant cost behind a
    single core not sustaining 15fps (see composite_recorder's module
    docstring / the wallclock-PTS fix in CompositeRecorder.start()).
    """

    def __init__(self, is_screenshare: bool, owner_sid: str) -> None:
        self.is_screenshare = is_screenshare
        #: The publishing participant's sid -- lets the compositor tell which
        #: participants already have a live camera image vs. need a
        #: placeholder tile instead (see CompositeRecorder._build_canvas).
        self.owner_sid = owner_sid
        self._latest_frame: rtc.VideoFrame | None = None
        self._task: asyncio.Task | None = None

    def start(self, track: rtc.RemoteVideoTrack) -> None:
        self._task = asyncio.create_task(self._read(track))

    async def _read(self, track: rtc.RemoteVideoTrack) -> None:
        stream = rtc.VideoStream(track)
        try:
            async for event in stream:
                self._latest_frame = event.frame
        except Exception:
            log.exception("video track reader crashed")
        finally:
            await stream.aclose()

    def image(self) -> Image.Image | None:
        frame = self._latest_frame
        if frame is None:
            return None
        rgba = frame.convert(rtc.VideoBufferType.RGBA)
        return Image.frombuffer(
            "RGBA", (rgba.width, rgba.height), bytes(rgba.data), "raw", "RGBA", 0, 1
        ).convert("RGB")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass


class AudioCapture:
    """One lossless WAV file per audio track; mixed together at finalize.

    Captured as WAV (not straight to AAC) specifically so the *only* lossy
    encode a lesson's audio goes through is the single AAC pass finalize()
    does after mixing -- capturing straight to AAC here meant every track
    got compressed once on the way in and then decoded, mixed and
    re-compressed *again* at finalize, and the second lossy pass on top of
    the first is exactly what made recorded audio sound worse than the
    live call."""

    def __init__(self, work_dir: str, sid: str, elapsed_ms) -> None:
        self.path = os.path.join(work_dir, f"audio-{sid}.wav")
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
                            "-c:a", "pcm_s16le", self.path,
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
    def __init__(self, work_dir: str, teacher_identity: str | None = None) -> None:
        self.work_dir = work_dir
        self.video_path = os.path.join(work_dir, "composite.video.mp4")
        self._videos: dict[str, VideoTrackState] = {}
        self._audios: dict[str, AudioCapture] = {}
        #: participant sid -> (identity, display name). identity is compared
        #: against teacher_identity for tile ordering; sid (not identity) is
        #: the dict key because it's what participant_connected/disconnected
        #: and track events hand us, and it's unique per connection even if
        #: someone reconnects mid-lesson.
        self._participants: dict[str, tuple[str, str]] = {}
        self._teacher_identity = teacher_identity
        self._encoder: subprocess.Popen | None = None
        self._compositor_task: asyncio.Task | None = None
        self._t0: float | None = None
        self._running = False

    # ---- track wiring ----
    def add_video(self, sid: str, track: rtc.RemoteVideoTrack, is_screenshare: bool, owner_sid: str) -> None:
        state = VideoTrackState(is_screenshare, owner_sid)
        state.start(track)
        self._videos[sid] = state
        log.info("video track added sid=%s screenshare=%s owner=%s (%d total)", sid, is_screenshare, owner_sid, len(self._videos))

    def add_audio(self, sid: str, track: rtc.RemoteAudioTrack) -> None:
        cap = AudioCapture(self.work_dir, sid, self._elapsed_ms)
        cap.start(track)
        self._audios[sid] = cap
        log.info("audio track added sid=%s (%d total)", sid, len(self._audios))

    def remove_track(self, sid: str) -> None:
        # A track sid is video XOR audio, never both -- check video first
        # since it's the common case, fall back to audio. The audio branch
        # only stops the capture early (ffmpeg process + reader task) to
        # free it as soon as the track actually ends, e.g. on a mid-lesson
        # reconnect (the normal way this happens on bad wifi) -- it does NOT
        # pop the entry out of _audios the way video does. finalize() mixes
        # every AudioCapture in that dict; popping here would drop whatever
        # this participant said before they disconnected from the final
        # recording instead of just freeing the now-idle process. stop() is
        # safe to call again from finalize()'s own cleanup loop -- closing
        # an already-closed pipe and waiting on an already-exited process
        # are both no-ops.
        vs = self._videos.pop(sid, None)
        if vs is not None:
            asyncio.create_task(vs.stop())
            log.info("video track removed sid=%s (%d left)", sid, len(self._videos))
            return
        cap = self._audios.get(sid)
        if cap is not None:
            asyncio.create_task(cap.stop())
            log.info("audio track ended sid=%s, released early", sid)

    def add_participant(self, sid: str, identity: str, name: str) -> None:
        self._participants[sid] = (identity, name or identity)
        log.info("participant joined identity=%s (%d in room)", identity, len(self._participants))

    def remove_participant(self, sid: str) -> None:
        self._participants.pop(sid, None)

    # ---- compositing ----
    def start(self) -> None:
        # Timestamp frames by arrival wallclock and let the fps filter rebuild
        # a constant 15fps from them. Treating the pipe as already-CFR would
        # mean a box that can't composite 15 times a second silently produces
        # a *time-compressed* lesson -- an hour of class encoded as 33 minutes,
        # picture drifting further ahead of the audio every minute. With
        # wallclock PTS a slow box just repeats frames: choppier, still true to
        # the clock, and duplicate frames are nearly free for x264.
        self._encoder = subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{CANVAS_W}x{CANVAS_H}", "-framerate", str(FPS),
                "-use_wallclock_as_timestamps", "1", "-i", "-",
                "-vf", f"fps={FPS}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                "-pix_fmt", "yuv420p", "-g", str(FPS * 2),
                self.video_path,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # self._t0 stays None here on purpose. ffmpeg's own PTS zero-point
        # (with -use_wallclock_as_timestamps) is the wallclock moment the
        # FIRST raw frame reaches its stdin -- not the moment this Popen()
        # returns. Process startup + libx264 init + waiting for the first
        # composite tick can be a real gap (worse under CPU pressure), and
        # every audio track's offset_ms is measured against this clock --
        # anchoring it here made every recording's audio start a fixed
        # amount late relative to the picture. Set on the first real write
        # instead, in _render_and_write().
        self._running = True
        self._compositor_task = asyncio.create_task(self._composite_loop())

    def _elapsed_ms(self) -> int:
        """Milliseconds since the first frame reached the encoder; 0 before then."""
        if self._t0 is None:
            return 0
        return max(0, int((time.monotonic() - self._t0) * 1000))

    def _build_canvas(
        self, videos: list[VideoTrackState], participants: dict[str, tuple[str, str]]
    ) -> Image.Image:
        canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), BLACK)
        screenshares = [v for v in videos if v.is_screenshare]
        cameras = [v for v in videos if not v.is_screenshare]

        share_img = None
        for v in screenshares:
            share_img = v.image()
            if share_img is not None:
                break

        cam_by_owner: dict[str, Image.Image] = {}
        for v in cameras:
            img = v.image()
            if img is not None:
                cam_by_owner[v.owner_sid] = img

        # One tile per participant currently in the room -- their live camera
        # if they've published one, a name/initials placeholder otherwise, so
        # a lesson where nobody's camera is on still shows who was there
        # instead of an empty canvas. Teacher first, students after (in join
        # order among themselves -- sort is stable).
        ordered_sids = sorted(
            participants, key=lambda sid: participants[sid][0] != self._teacher_identity
        )
        cam_imgs = [
            cam_by_owner[sid] if sid in cam_by_owner else _placeholder_image(participants[sid][1])
            for sid in ordered_sids
        ]

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
        # else: nobody has joined yet -> black frame (keeps the encoder alive)
        return canvas

    def _render_and_write(
        self, videos: list[VideoTrackState], participants: dict[str, tuple[str, str]]
    ) -> None:
        canvas = self._build_canvas(videos, participants)
        if self._encoder and self._encoder.stdin:
            if self._t0 is None:
                self._t0 = time.monotonic()
            self._encoder.stdin.write(canvas.tobytes())

    async def _composite_loop(self) -> None:
        loop = asyncio.get_event_loop()
        frame_interval = 1.0 / FPS
        next_t = loop.time()
        while self._running:
            try:
                # Snapshot the tracks (and the participant roster, for
                # ordering/placeholders) here, on the event-loop thread, so
                # neither dict can change mid-iteration; then resize and push
                # the 2.7 MB frame off-thread -- a full ffmpeg pipe would
                # otherwise stall this loop and every track reader with it.
                await loop.run_in_executor(
                    None, self._render_and_write, list(self._videos.values()), dict(self._participants)
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
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", out_path,
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


async def run(
    room_name: str,
    token: str,
    url: str,
    s3_settings: dict,
    teacher_id: str | None = None,
    max_seconds: int = 4 * 3600,
) -> bool:
    """Returns True if the lesson was a genuine no-show (nobody ever joined
    within _INITIAL_JOIN_TIMEOUT_SECONDS) -- see NO_SHOW_EXIT_CODE."""
    work_dir = tempfile.mkdtemp(prefix=f"rec-{room_name}-")
    recorder = CompositeRecorder(work_dir, teacher_identity=teacher_id)
    room = rtc.Room()

    # The compositor (and the ffmpeg encoder underneath it) only starts once
    # someone's actually in the room. Starting it unconditionally on connect
    # meant a lesson nobody ever joins still burned a full encode slot --
    # of only MAX_CONCURRENT_RECORDINGS total -- and produced 45 minutes of
    # plain black video that then got uploaded for no one.
    started = False

    def _ensure_started() -> None:
        nonlocal started
        if not started:
            started = True
            recorder.start()

    # SIGTERM is what a deploy/redeploy (`docker compose up -d --build`, run
    # on every push -- see .github/workflows/deploy-backend.yml) sends this
    # process. Left uncaught, the process just dies mid-recording and
    # finalize() below -- which mixes the audio and uploads to S3 -- never
    # runs, silently losing the whole lesson recorded so far rather than
    # just the last few seconds. Treat it as one more reason to fall out of
    # the wait loop and go through the same finalize/upload path an empty
    # room does.
    loop = asyncio.get_event_loop()
    shutdown_requested = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_requested.set)

    def _wire(track, publication, participant) -> None:
        if track.kind == rtc.TrackKind.KIND_VIDEO:
            recorder.add_video(track.sid, track, _is_screenshare(publication), participant.sid)
        elif track.kind == rtc.TrackKind.KIND_AUDIO:
            recorder.add_audio(track.sid, track)

    @room.on("participant_connected")
    def on_participant_connected(participant):
        _ensure_started()
        recorder.add_participant(participant.sid, participant.identity, participant.name)

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        recorder.remove_participant(participant.sid)

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        _wire(track, publication, participant)

    @room.on("track_unsubscribed")
    def on_track_unsubscribed(track, publication, participant):
        recorder.remove_track(track.sid)

    log.info("connecting to room %s", room_name)
    await room.connect(url, token, options=rtc.RoomOptions(auto_subscribe=True))
    log.info("connected, %d participants already present", len(room.remote_participants))
    if room.remote_participants:
        _ensure_started()
    for p in room.remote_participants.values():
        recorder.add_participant(p.sid, p.identity, p.name)
        for pub in p.track_publications.values():
            if pub.track is not None:
                _wire(pub.track, pub, p)

    # Driven by the clock (start_time/max_seconds, both set from the
    # lesson's own scheduled_start/scheduled_end -- see watcher.py), not by
    # participants coming and going: the room briefly emptying (a reload, a
    # wifi blip) no longer ends the recording early. Previously a 10-second
    # empty-room grace did exactly that, and on a lesson with any amount of
    # reconnecting it meant a fresh recorder process (and a fresh uploaded
    # file) every time the room happened to be empty for 10 seconds --
    # a single lesson coming out as a pile of 5-10 minute clips instead of
    # one recording. The only way out early now is a genuine no-show.
    ever_had_participant = len(room.remote_participants) > 0
    no_show = False
    start_time = loop.time()
    while True:
        await asyncio.sleep(3)
        now = loop.time()
        if shutdown_requested.is_set():
            log.info("shutdown requested, finalizing composite recording for %s", room_name)
            break
        if len(room.remote_participants) > 0:
            ever_had_participant = True
        elif not ever_had_participant and now - start_time >= _INITIAL_JOIN_TIMEOUT_SECONDS:
            log.info("nobody joined %s within %ds, giving up", room_name, _INITIAL_JOIN_TIMEOUT_SECONDS)
            no_show = True
            break
        if now - start_time >= max_seconds:
            log.warning("hit the %ds safety cap for %s, stopping regardless of room state", max_seconds, room_name)
            break

    log.info("finalizing composite recording for %s", room_name)
    await room.disconnect()

    if not ever_had_participant:
        log.info("nobody ever joined %s, nothing to upload", room_name)
        shutil.rmtree(work_dir, ignore_errors=True)
        return no_show

    path = await recorder.finalize(room_name)
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        log.warning("nothing recorded, nothing to upload")
        shutil.rmtree(work_dir, ignore_errors=True)
        return False

    client = Minio(
        s3_settings["endpoint"], access_key=s3_settings["access_key"],
        secret_key=s3_settings["secret_key"], secure=s3_settings["secure"], region="auto",
    )
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    object_name = f"{room_name}/{timestamp}.mp4"
    client.fput_object(s3_settings["bucket"], object_name, path)
    log.info("uploaded composite (%d bytes) -> %s", os.path.getsize(path), object_name)

    shutil.rmtree(work_dir, ignore_errors=True)
    log.info("done")
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--room", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--s3-endpoint", required=True)
    parser.add_argument("--s3-access-key", required=True)
    parser.add_argument("--s3-secret-key", required=True)
    # False for our own self-hosted MinIO (internal Docker network, no TLS);
    # True for a real cloud bucket (Backblaze/R2/S3).
    parser.add_argument("--s3-secure", type=int, default=1)
    parser.add_argument("--s3-bucket", required=True)
    # The lesson's teacher_id (from calendar.lessons), so the teacher's tile
    # sorts first. Optional: watcher.py only passes it in composite mode.
    parser.add_argument("--teacher-id", default=None)
    parser.add_argument("--max-seconds", type=int, default=4 * 3600)
    args = parser.parse_args()

    s3_settings = {
        "endpoint": args.s3_endpoint,
        "access_key": args.s3_access_key,
        "secret_key": args.s3_secret_key,
        "bucket": args.s3_bucket,
        "secure": bool(args.s3_secure),
    }
    no_show = asyncio.run(
        run(
            args.room,
            args.token,
            args.url,
            s3_settings,
            teacher_id=args.teacher_id,
            max_seconds=args.max_seconds,
        )
    )
    return NO_SHOW_EXIT_CODE if no_show else 0


if __name__ == "__main__":
    sys.exit(main())
