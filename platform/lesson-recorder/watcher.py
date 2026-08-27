"""Polls the calendar schema for lessons currently in progress and spawns
recorder_bot.py for each one that doesn't already have a recorder running --
capped at MAX_CONCURRENT_RECORDINGS, since encoding video is expensive on
a small shared server (measured: ~1.7-1.9 load-average per concurrent
recording). A lesson that's live while every slot is full simply goes
unrecorded; it never blocks the lesson itself, only the recording.

Recording bucket credentials empty/unset is a valid, expected "recording
isn't configured yet" state (matches calendar's own recordings.py) -- the
watcher just idles rather than crash-looping.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
import signal
import subprocess
import uuid

import asyncpg
from livekit import api as lk_api

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("recorder-watcher")

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "")

LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")

RECORDINGS_S3_ENDPOINT = os.environ.get("RECORDINGS_S3_ENDPOINT", "")
RECORDINGS_S3_ACCESS_KEY = os.environ.get("RECORDINGS_S3_ACCESS_KEY", "")
RECORDINGS_S3_SECRET_KEY = os.environ.get("RECORDINGS_S3_SECRET_KEY", "")
RECORDINGS_S3_BUCKET = os.environ.get("RECORDINGS_S3_BUCKET", "")

MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_RECORDINGS", "2"))
POLL_SECONDS = 20
# If a lesson is still going at its scheduled_end, keep recording this much
# longer before the recorder's own safety cap cuts it off regardless.
END_OF_LESSON_BUFFER_SECONDS = 15 * 60
# Must match NO_SHOW_EXIT_CODE in composite_recorder.py / recorder_bot.py --
# the exit code either script uses to report "nobody ever joined, gave up"
# (see their own _INITIAL_JOIN_TIMEOUT_SECONDS), so _reap_finished can flip
# the lesson to missed right away instead of waiting for it to read as
# missed on its own once scheduled_end passes.
NO_SHOW_EXIT_CODE = 2
# How long to give active recordings to finish their own graceful shutdown
# (ffmpeg finalize + the S3 upload -- can be real time for an hour-long
# lesson) once this watcher gets SIGTERM, before giving up and killing them
# outright. Keep in step with the `recorder` service's stop_grace_period in
# docker-compose.yml -- Docker SIGKILLs the whole container once that
# elapses regardless of what this is still waiting on.
SHUTDOWN_DRAIN_SECONDS = 180

# "composite" -> one screenshare-first MP4 per lesson (composite_recorder.py);
# "per_participant" -> a file per camera (recorder_bot.py, the old behaviour,
# kept as a one-env-var rollback). Composite's encode cost is constant in the
# participant count, so it's the default now.
RECORDING_MODE = os.environ.get("RECORDING_MODE", "composite").strip().lower()
_RECORDER_SCRIPT = "composite_recorder.py" if RECORDING_MODE == "composite" else "recorder_bot.py"

_active: dict[str, subprocess.Popen] = {}  # lesson_id -> bot process


def _is_configured() -> bool:
    return bool(
        LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET
        and RECORDINGS_S3_ENDPOINT and RECORDINGS_S3_ACCESS_KEY
        and RECORDINGS_S3_SECRET_KEY and RECORDINGS_S3_BUCKET
    )


# Never given a display name on purpose: with no name, LiveKit clients
# render this participant under its bare identity ("recorder-bot") instead
# of a human-facing label -- which is exactly what the frontend's call page
# targets (see the <style> block in the lesson call page) to hide this
# participant's placeholder tile from the two real participants.
RECORDER_IDENTITY = "recorder-bot"


def _mint_token(room: str) -> str:
    grants = lk_api.VideoGrants(room_join=True, room=room, can_publish=False, can_subscribe=True)
    return (
        lk_api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(RECORDER_IDENTITY)
        .with_grants(grants)
        .to_jwt()
    )


async def _mark_missed(pool: asyncpg.Pool, lesson_id: str) -> None:
    """The recorder gave up because nobody ever joined within the no-show
    window. Flip the lesson to 'missed' right away instead of waiting for
    it to read as missed on its own once scheduled_end passes (see
    calendar's LessonStatus/_lesson_out) -- guarded on still being
    'scheduled' so this can never clobber a status someone already changed
    by hand (e.g. cancelled it) while the recorder was waiting."""
    result = await pool.execute(
        "UPDATE calendar.lessons SET status = 'missed' WHERE id = $1 AND status = 'scheduled'",
        uuid.UUID(lesson_id),
    )
    if result == "UPDATE 1":
        log.info("marked lesson %s as missed (nobody ever joined)", lesson_id)


async def _reap_finished(pool: asyncpg.Pool | None) -> None:
    for lesson_id in list(_active):
        proc = _active[lesson_id]
        if proc.poll() is not None:
            log.info("recording for lesson %s finished (exit=%s)", lesson_id, proc.returncode)
            del _active[lesson_id]
            if proc.returncode == NO_SHOW_EXIT_CODE and pool is not None:
                await _mark_missed(pool, lesson_id)


async def _shutdown(pool: asyncpg.Pool | None) -> None:
    """Forward SIGTERM to every active recorder subprocess and wait for them
    to actually exit before this process -- the container's PID 1 -- returns
    and lets the container itself be torn down. Each recorder script (see
    composite_recorder.py/recorder_bot.py) handles SIGTERM by finalizing and
    uploading whatever it's captured so far, same as a normal empty-room
    exit; exiting immediately instead of waiting for that would tear the
    container (and every process in it) down under them regardless, losing
    the recording just the same as not forwarding the signal at all."""
    if not _active:
        return
    log.info("shutting down: sending SIGTERM to %d active recording(s)", len(_active))
    for proc in _active.values():
        proc.terminate()
    deadline = asyncio.get_event_loop().time() + SHUTDOWN_DRAIN_SECONDS
    while _active and asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(1)
        await _reap_finished(pool)
    if _active:
        log.warning("%d recording(s) still running at the shutdown deadline, killing them", len(_active))
        for proc in _active.values():
            proc.kill()


async def poll_once(pool: asyncpg.Pool) -> None:
    await _reap_finished(pool)

    rows = await pool.fetch(
        "SELECT id, scheduled_end, teacher_id FROM calendar.lessons "
        "WHERE status = 'scheduled' AND scheduled_start <= now() AND scheduled_end >= now()"
    )

    for row in rows:
        lesson_id = str(row["id"])
        if lesson_id in _active:
            continue
        if len(_active) >= MAX_CONCURRENT:
            log.warning(
                "lesson %s is live but %d/%d recording slots are full -- skipping this lesson",
                lesson_id, len(_active), MAX_CONCURRENT,
            )
            continue

        room = f"lesson-{lesson_id}"
        remaining = (row["scheduled_end"] - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        max_seconds = max(int(remaining) + END_OF_LESSON_BUFFER_SECONDS, END_OF_LESSON_BUFFER_SECONDS)
        token = _mint_token(room)
        cmd = [
            "python", _RECORDER_SCRIPT,
            "--room", room, "--token", token, "--url", LIVEKIT_URL,
            "--s3-endpoint", RECORDINGS_S3_ENDPOINT,
            "--s3-access-key", RECORDINGS_S3_ACCESS_KEY,
            "--s3-secret-key", RECORDINGS_S3_SECRET_KEY,
            "--s3-bucket", RECORDINGS_S3_BUCKET,
            "--max-seconds", str(max_seconds),
        ]
        if RECORDING_MODE == "composite":
            # recorder_bot.py (the per-participant fallback) has no concept
            # of tile ordering, so it doesn't take this flag.
            cmd += ["--teacher-id", str(row["teacher_id"])]
        proc = subprocess.Popen(cmd)
        _active[lesson_id] = proc
        log.info("started recording for lesson %s (%d/%d slots used)", lesson_id, len(_active), MAX_CONCURRENT)


async def main() -> None:
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    if not _is_configured():
        log.warning("LIVEKIT_*/RECORDINGS_S3_* not fully set -- recording is disabled, idling forever")
        await shutdown_event.wait()
        await _shutdown(None)
        return

    pool = await asyncpg.create_pool(
        host=POSTGRES_HOST, port=POSTGRES_PORT, user=POSTGRES_USER,
        password=POSTGRES_PASSWORD, database=POSTGRES_DB,
    )
    log.info(
        "recorder watcher started -- mode=%s script=%s max concurrent=%d, polling every %ds",
        RECORDING_MODE, _RECORDER_SCRIPT, MAX_CONCURRENT, POLL_SECONDS,
    )
    while not shutdown_event.is_set():
        try:
            await poll_once(pool)
        except Exception:
            log.exception("poll failed")
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=POLL_SECONDS)
        except asyncio.TimeoutError:
            pass
    await _shutdown(pool)


if __name__ == "__main__":
    asyncio.run(main())
