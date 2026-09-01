"""Lesson recordings.

A dedicated `lesson-recorder` service (see `platform/lesson-recorder/`)
joins each lesson's LiveKit room as a hidden participant and uploads
per-participant MP4 files straight to an S3-compatible bucket -- not
LiveKit's own paid Egress. That swap happened because LiveKit Cloud's
free egress-minute quota couldn't cover this platform's real lesson
volume and the paid tier's per-minute cost didn't pencil out (see the
recorder service's own docs for the numbers).

The bucket itself is our own self-hosted MinIO, which -- like every other
internal service -- is never exposed to the public internet (see
content's `storage.py` for the same call). So unlike a real cloud bucket,
a presigned MinIO URL would only resolve from inside the Docker network,
not from a student's browser. Recordings are therefore streamed back
through this department's own API (`GET .../recordings/{object}/stream`
in api/routes/calendar.py) instead of a presigned link -- this module just
hands that route the raw object body to relay.

This module only ever reads the bucket back -- it has no part in writing
recordings, and nothing about a recording is persisted in our own
database: "does this lesson have a recording, and where" is answered by
listing the bucket under this room's own prefix, the same way a join
token is minted fresh rather than stored (see livekit_client.py).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import BinaryIO

from minio import Minio

from ..core.config import get_settings

_settings = get_settings()

_client: Minio | None = (
    Minio(
        _settings.recordings_s3_endpoint,
        access_key=_settings.recordings_s3_access_key,
        secret_key=_settings.recordings_s3_secret_key,
        secure=_settings.recordings_s3_secure,
        region="auto",
    )
    if _settings.recordings_s3_endpoint
    else None
)


class RecordingError(Exception):
    pass


def is_configured() -> bool:
    return _client is not None


async def list_recordings(room: str) -> list[dict]:
    """Every uploaded recording for this room, without a playback URL --
    the caller (the API route) fills that in, since it's the one that
    knows the request's own auth token and public path prefix. A room
    that was never joined, or joined before recording was configured,
    just has none -- not an error."""
    if not is_configured():
        return []
    out: list[dict] = []
    for obj in _client.list_objects(_settings.recordings_s3_bucket, prefix=f"{room}/", recursive=True):
        out.append(
            {
                "object_name": obj.object_name,
                "started_at": obj.last_modified,
                "ended_at": None,
                "duration_seconds": None,
            }
        )
    out.sort(key=lambda r: r["started_at"] or datetime.min.replace(tzinfo=timezone.utc))
    return out


def open_recording(object_name: str) -> BinaryIO:
    """The raw object body (a urllib3 response), for the API route to
    relay to the browser via StreamingResponse. Caller must close() +
    release_conn() when done -- see get_public_file in content's
    storage.py for the same shape."""
    if not is_configured():
        raise RecordingError("Recordings are not configured on this server")
    return _client.get_object(_settings.recordings_s3_bucket, object_name)


def delete_recording(object_name: str) -> None:
    if not is_configured():
        raise RecordingError("Recordings are not configured on this server")
    _client.remove_object(_settings.recordings_s3_bucket, object_name)
