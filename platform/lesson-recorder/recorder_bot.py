"""Records one LiveKit room to per-participant MP4 files and uploads them to
Backblaze. Joins as a hidden participant (publishes nothing, subscribes to
everyone) -- no LiveKit Egress involved, so no LiveKit Cloud minutes spent.

Each remote participant's audio and video tracks are captured to separate
raw streams (ffmpeg can't cleanly take two independent live raw inputs on
one process without a lot of pipe-juggling), then muxed together into one
file per participant once the room empties. A participant with camera off
just gets an audio-only file -- both cases upload fine, the existing
recordings UI already renders a list, not a single fixed file.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile

from livekit import rtc
from minio import Minio

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("recorder-bot")

# The watcher spawns this bot proactively at the lesson's scheduled start,
# not when someone actually joins, and the recording window follows the
# lesson's own clock (max_seconds, from scheduled_end -- see watcher.py),
# not participant presence: the room going briefly empty (a reload, a wifi
# blip) no longer ends anyone's recording early, same reasoning as
# composite_recorder.py's run(). Only a genuine "nobody ever showed up"
# case still cuts things short, via this timeout.
_INITIAL_JOIN_TIMEOUT_SECONDS = 45 * 60
# Process exit code signalling "nobody ever joined, gave up" -- must match
# composite_recorder.py's own copy of this constant; watcher.py checks for
# exactly this to mark the lesson missed right away.
NO_SHOW_EXIT_CODE = 2


class ParticipantRecorder:
    def __init__(self, identity: str, work_dir: str) -> None:
        self.identity = identity
        self.work_dir = work_dir
        self.video_path = os.path.join(work_dir, f"{identity}.video.mp4")
        self.audio_path = os.path.join(work_dir, f"{identity}.audio.m4a")
        self.has_video = False
        self.has_audio = False
        self._video_proc: subprocess.Popen | None = None
        self._audio_proc: subprocess.Popen | None = None
        self._tasks: list[asyncio.Task] = []

    def start_video(self, track: rtc.RemoteVideoTrack) -> None:
        self._tasks.append(asyncio.create_task(self._record_video(track)))

    def start_audio(self, track: rtc.RemoteAudioTrack) -> None:
        self._tasks.append(asyncio.create_task(self._record_audio(track)))

    async def _record_video(self, track: rtc.RemoteVideoTrack) -> None:
        stream = rtc.VideoStream(track)
        try:
            async for event in stream:
                frame = event.frame.convert(rtc.VideoBufferType.I420)
                if self._video_proc is None:
                    self._video_proc = subprocess.Popen(
                        [
                            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p",
                            "-s", f"{frame.width}x{frame.height}",
                            "-use_wallclock_as_timestamps", "1", "-i", "-",
                            "-vf", "scale=-2:'min(720,ih)',fps=15",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p",
                            self.video_path,
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.has_video = True
                    log.info("%s: video started (%sx%s)", self.identity, frame.width, frame.height)
                try:
                    self._video_proc.stdin.write(bytes(frame.data))
                except (BrokenPipeError, OSError):
                    break
        finally:
            await stream.aclose()
            self._close_proc(self._video_proc)

    async def _record_audio(self, track: rtc.RemoteAudioTrack) -> None:
        stream = rtc.AudioStream(track)
        try:
            async for event in stream:
                frame = event.frame
                if self._audio_proc is None:
                    self._audio_proc = subprocess.Popen(
                        [
                            "ffmpeg", "-y", "-f", "s16le",
                            "-ar", str(frame.sample_rate), "-ac", str(frame.num_channels),
                            "-use_wallclock_as_timestamps", "1", "-i", "-",
                            "-c:a", "aac", "-b:a", "128k", self.audio_path,
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.has_audio = True
                    log.info("%s: audio started (%sHz, %sch)", self.identity, frame.sample_rate, frame.num_channels)
                try:
                    self._audio_proc.stdin.write(bytes(frame.data))
                except (BrokenPipeError, OSError):
                    break
        finally:
            await stream.aclose()
            self._close_proc(self._audio_proc)

    @staticmethod
    def _close_proc(proc: subprocess.Popen | None) -> None:
        if proc is None:
            return
        try:
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        proc.wait(timeout=15)

    async def finalize(self) -> str | None:
        """Waits for the capture tasks to actually finish flushing, then
        muxes audio+video (or just renames whichever single one exists)."""
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

        out_path = os.path.join(self.work_dir, f"{self.identity}.mp4")
        if self.has_video and self.has_audio:
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", self.video_path, "-i", self.audio_path,
                    "-c:v", "copy", "-c:a", "copy", "-shortest",
                    "-movflags", "+faststart", out_path,
                ],
                capture_output=True,
            )
            if result.returncode != 0:
                log.warning("%s: mux failed: %s", self.identity, result.stderr.decode(errors="replace")[-500:])
                return self.video_path if os.path.exists(self.video_path) else None
            return out_path
        if self.has_video:
            # Same reasoning as the combined-mux branch above: relocate the
            # moov atom to the front (cheap remux, -c copy so no re-encode)
            # so playback can start before the whole file has downloaded.
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", self.video_path, "-c", "copy", "-movflags", "+faststart", out_path],
                capture_output=True,
            )
            return out_path if result.returncode == 0 else self.video_path
        if self.has_audio:
            return self.audio_path
        return None


async def run(room_name: str, token: str, url: str, s3_settings: dict, max_seconds: int = 4 * 3600) -> bool:
    """Returns True if the lesson was a genuine no-show (nobody ever joined
    within _INITIAL_JOIN_TIMEOUT_SECONDS) -- see NO_SHOW_EXIT_CODE."""
    work_dir = tempfile.mkdtemp(prefix=f"rec-{room_name}-")
    recorders: dict[str, ParticipantRecorder] = {}
    room = rtc.Room()

    # See composite_recorder.py's run() for why this matters: without it, a
    # deploy's SIGTERM kills this process mid-recording and every
    # participant's finalize()/upload below never runs.
    loop = asyncio.get_event_loop()
    shutdown_requested = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_requested.set)

    def _recorder_for(identity: str) -> ParticipantRecorder:
        if identity not in recorders:
            recorders[identity] = ParticipantRecorder(identity, work_dir)
        return recorders[identity]

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        rec = _recorder_for(participant.identity)
        if track.kind == rtc.TrackKind.KIND_VIDEO:
            rec.start_video(track)
        elif track.kind == rtc.TrackKind.KIND_AUDIO:
            rec.start_audio(track)

    log.info("connecting to room %s", room_name)
    await room.connect(url, token, options=rtc.RoomOptions(auto_subscribe=True))
    log.info("connected, %d participants already present", len(room.remote_participants))
    for p in room.remote_participants.values():
        for pub in p.track_publications.values():
            if pub.track is not None:
                rec = _recorder_for(p.identity)
                if pub.track.kind == rtc.TrackKind.KIND_VIDEO:
                    rec.start_video(pub.track)
                elif pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                    rec.start_audio(pub.track)

    # Driven by the clock (start_time/max_seconds, from the lesson's own
    # scheduled_start/scheduled_end -- see watcher.py), not by participants
    # coming and going -- see composite_recorder.py's run() for why. Only a
    # genuine no-show still gives up early.
    ever_had_participant = len(room.remote_participants) > 0
    no_show = False
    start_time = loop.time()
    while True:
        await asyncio.sleep(3)
        now = loop.time()
        if shutdown_requested.is_set():
            log.info("shutdown requested, finalizing %d participant recording(s) for %s", len(recorders), room_name)
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

    log.info("finalizing %d participant recording(s) for %s", len(recorders), room_name)
    await room.disconnect()

    if not ever_had_participant:
        log.info("nobody ever joined %s, nothing to upload", room_name)
        shutil.rmtree(work_dir, ignore_errors=True)
        return no_show

    client = Minio(
        s3_settings["endpoint"], access_key=s3_settings["access_key"],
        secret_key=s3_settings["secret_key"], secure=s3_settings["secure"], region="auto",
    )
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    for identity, rec in recorders.items():
        path = await rec.finalize()
        if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
            log.warning("%s: nothing recorded, skipping upload", identity)
            continue
        object_name = f"{room_name}/{timestamp}-{identity}.mp4"
        client.fput_object(s3_settings["bucket"], object_name, path)
        log.info("uploaded %s (%d bytes) -> %s", identity, os.path.getsize(path), object_name)

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
    parser.add_argument("--s3-bucket", required=True)
    parser.add_argument("--s3-secure", type=int, default=1)
    parser.add_argument("--max-seconds", type=int, default=4 * 3600)
    args = parser.parse_args()

    s3_settings = {
        "endpoint": args.s3_endpoint,
        "access_key": args.s3_access_key,
        "secret_key": args.s3_secret_key,
        "bucket": args.s3_bucket,
        "secure": bool(args.s3_secure),
    }
    no_show = asyncio.run(run(args.room, args.token, args.url, s3_settings, args.max_seconds))
    return NO_SHOW_EXIT_CODE if no_show else 0


if __name__ == "__main__":
    sys.exit(main())
