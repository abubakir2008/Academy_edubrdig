"""Lesson recordings: LiveKit's auto-egress uploads the finished file
directly to an S3-compatible bucket (Cloudflare R2) from LiveKit Cloud's own
infrastructure -- this department never receives or stores the video bytes,
only (a) tells LiveKit to attach recording to a room when the lesson is
created, and (b) mints short-lived presigned URLs to read a finished
recording back.

Nothing about a recording is persisted in our own database: "does this
lesson have a recording, and where" is answered by asking LiveKit's Egress
API for the room, the same way a join token is minted fresh rather than
stored (see livekit_client.py) -- one less thing that can drift out of sync
with reality.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from livekit import api as lk_api
from minio import Minio

from ..core.config import get_settings

_settings = get_settings()

_client: Minio | None = (
    Minio(
        _settings.recordings_s3_endpoint,
        access_key=_settings.recordings_s3_access_key,
        secret_key=_settings.recordings_s3_secret_key,
        secure=True,
        region="auto",
    )
    if _settings.recordings_s3_endpoint
    else None
)


class RecordingError(Exception):
    pass


def is_configured() -> bool:
    return _client is not None


def _lk_http_url() -> str:
    # The server SDK's REST client wants http(s); the browser's LiveKit
    # client is the one that connects with wss://.
    return _settings.livekit_url.replace("wss://", "https://").replace("ws://", "http://")


def _lk_api() -> lk_api.LiveKitAPI:
    return lk_api.LiveKitAPI(
        url=_lk_http_url(), api_key=_settings.livekit_api_key, api_secret=_settings.livekit_api_secret
    )


async def ensure_room_with_recording(room: str) -> None:
    """Pre-creates the LiveKit room with auto-egress attached, so recording
    starts the moment the first participant joins and stops automatically
    once the room empties (LiveKit ties RoomComposite egress to the room's
    own lifecycle) -- no separate start/stop call needed from us. Best-effort:
    a lesson is still fully usable, just unrecorded, if this fails or
    recording isn't configured at all.
    """
    if not is_configured():
        return
    async with _lk_api() as lkapi:
        await lkapi.room.create_room(
            lk_api.CreateRoomRequest(
                name=room,
                egress=lk_api.RoomEgress(
                    room=lk_api.RoomCompositeEgressRequest(
                        # Explicit rather than relying on LiveKit's implicit
                        # default -- "speaker" is one of their own hosted,
                        # documented compositor layouts.
                        layout="speaker",
                        file_outputs=[
                            lk_api.EncodedFileOutput(
                                file_type=lk_api.EncodedFileType.MP4,
                                filepath="{room_name}/{time}.mp4",
                                s3=lk_api.S3Upload(
                                    access_key=_settings.recordings_s3_access_key,
                                    secret=_settings.recordings_s3_secret_key,
                                    bucket=_settings.recordings_s3_bucket,
                                    endpoint=f"https://{_settings.recordings_s3_endpoint}",
                                    region="auto",
                                    force_path_style=True,
                                ),
                            )
                        ],
                    )
                ),
            )
        )


def _ns_to_dt(ns: int) -> datetime | None:
    return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc) if ns else None


async def list_recordings(room: str) -> list[dict]:
    """Every finished recording for this room, each file signed for
    playback. A room that was never joined, or joined before recording was
    configured, just has none -- not an error."""
    if not is_configured():
        return []
    async with _lk_api() as lkapi:
        resp = await lkapi.egress.list_egress(lk_api.ListEgressRequest(room_name=room))
    out: list[dict] = []
    for info in resp.items:
        if info.status != lk_api.EgressStatus.EGRESS_COMPLETE:
            continue
        # A RoomCompositeEgressRequest with a single file_outputs entry (our
        # only configuration) comes back in the legacy singular `file` field,
        # not the newer `file_results` list -- LiveKit keeps both around for
        # backward compatibility but only populates one depending on how the
        # egress was requested. Without this fallback every recording made
        # through this department reads back as "none", even though the file
        # genuinely made it to the bucket.
        files = list(info.file_results) or ([info.file] if info.file.filename else [])
        for f in files:
            out.append(
                {
                    "object_name": f.filename,
                    "started_at": _ns_to_dt(info.started_at),
                    "ended_at": _ns_to_dt(info.ended_at),
                    "duration_seconds": int(f.duration / 1_000_000_000) if f.duration else None,
                    "url": _client.presigned_get_object(
                        _settings.recordings_s3_bucket, f.filename, expires=timedelta(hours=6)
                    ),
                }
            )
    out.sort(key=lambda r: r["started_at"] or datetime.min.replace(tzinfo=timezone.utc))
    return out


def delete_recording(object_name: str) -> None:
    if not is_configured():
        raise RecordingError("Recordings are not configured on this server")
    _client.remove_object(_settings.recordings_s3_bucket, object_name)
