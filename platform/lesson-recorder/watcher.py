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
import subprocess

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
END_OF_LESSON_BUFFER_SECONDS = 30 * 60

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


def _mint_token(room: str) -> str:
    grants = lk_api.VideoGrants(room_join=True, room=room, can_publish=False, can_subscribe=True)
    return (
        lk_api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity("recorder-bot")
        .with_name("Recorder")
        .with_grants(grants)
        .to_jwt()
    )


def _reap_finished() -> None:
    for lesson_id in list(_active):
        proc = _active[lesson_id]
        if proc.poll() is not None:
            log.info("recording for lesson %s finished (exit=%s)", lesson_id, proc.returncode)
            del _active[lesson_id]


async def poll_once(pool: asyncpg.Pool) -> None:
    _reap_finished()

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
    if not _is_configured():
        log.warning("LIVEKIT_*/RECORDINGS_S3_* not fully set -- recording is disabled, idling forever")
        while True:
            await asyncio.sleep(3600)

    pool = await asyncpg.create_pool(
        host=POSTGRES_HOST, port=POSTGRES_PORT, user=POSTGRES_USER,
        password=POSTGRES_PASSWORD, database=POSTGRES_DB,
    )
    log.info(
        "recorder watcher started -- mode=%s script=%s max concurrent=%d, polling every %ds",
        RECORDING_MODE, _RECORDER_SCRIPT, MAX_CONCURRENT, POLL_SECONDS,
    )
    while True:
        try:
            await poll_once(pool)
        except Exception:
            log.exception("poll failed")
        await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
