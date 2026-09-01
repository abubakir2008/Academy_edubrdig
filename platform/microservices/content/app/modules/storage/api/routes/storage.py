"""Storage endpoints (namespaced under /storage) backed by MinIO."""

from __future__ import annotations

import io
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from edubridge_shared.fastapi_auth import CurrentUser, has_any_role
from edubridge_shared.roles import STAFF_ROLES

from ...core.config import get_settings
from ...storage import client as internal_client
from ...storage import public_client as client
from ..deps import get_current_user

router = APIRouter(prefix="/storage", tags=["storage"])
_settings = get_settings()
_ALLOWED = {b.strip() for b in _settings.default_buckets.split(",")}

# Buckets a browser may read/write directly through this API (server-side —
# see upload_file/get_public_file below), not via a presigned MinIO URL.
# Kept narrow on purpose: this is the only path that works without MinIO
# being reachable from the public internet (it isn't — see storage.py).
# "avatars" is small public images; "materials" is homework submissions
# (essays, PDFs) — bigger files, broader types, still not public documents
# in the sense of being browsable, just fetchable by anyone holding the URL
# (same as avatars — no per-object auth on the read side, see get_public_file).
_DIRECT_BUCKETS = {"avatars", "materials"}
_ALLOWED_CONTENT_TYPES: dict[str, set[str]] = {
    "avatars": {"image/jpeg", "image/png", "image/webp", "image/gif"},
    "materials": {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    },
}
_MAX_UPLOAD_BYTES: dict[str, int] = {
    "avatars": 5 * 1024 * 1024,
    "materials": 20 * 1024 * 1024,
}


class PresignUpload(BaseModel):
    bucket: str = Field(description="one of the configured buckets")
    filename: str = Field(max_length=255)
    expires_seconds: int = Field(default=3600, ge=60, le=604800)


class PresignDownload(BaseModel):
    bucket: str
    object_name: str
    expires_seconds: int = Field(default=3600, ge=60, le=604800)


def _check_bucket(bucket: str) -> None:
    if bucket not in _ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unknown bucket. Allowed: {sorted(_ALLOWED)}")


@router.post("/presign-upload")
async def presign_upload(
    payload: PresignUpload, user: CurrentUser = Depends(get_current_user)
) -> dict:
    _check_bucket(payload.bucket)
    # Namespaced by user to prevent collisions/overwrites.
    object_name = f"{user.id}/{uuid.uuid4().hex}-{payload.filename}"
    try:
        url = client.presigned_put_object(
            payload.bucket, object_name, expires=timedelta(seconds=payload.expires_seconds)
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}") from exc
    return {"upload_url": url, "bucket": payload.bucket, "object_name": object_name, "method": "PUT"}


@router.post("/presign-download")
async def presign_download(
    payload: PresignDownload, user: CurrentUser = Depends(get_current_user)
) -> dict:
    _check_bucket(payload.bucket)
    # Objects are namespaced `{user_id}/...` (see presign_upload/upload_file
    # above) — without this check any authenticated user could presign a
    # download for any other user's object just by guessing/observing its
    # name. Staff can still reach any object (e.g. moderating an upload).
    if not payload.object_name.startswith(f"{user.id}/") and not has_any_role(
        user.role, STAFF_ROLES
    ):
        raise HTTPException(status_code=403, detail="Not your object")
    try:
        url = client.presigned_get_object(
            payload.bucket, payload.object_name, expires=timedelta(seconds=payload.expires_seconds)
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}") from exc
    return {"download_url": url, "bucket": payload.bucket, "object_name": payload.object_name}


@router.post("/upload")
async def upload_file(
    bucket: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Server-side upload for `_DIRECT_BUCKETS` — the file goes browser →
    this API → MinIO over the internal Docker network, instead of a
    presigned PUT straight to MinIO (which would need MinIO itself exposed
    on the public internet)."""
    if bucket not in _DIRECT_BUCKETS:
        raise HTTPException(status_code=400, detail=f"Direct upload only supports: {sorted(_DIRECT_BUCKETS)}")
    if file.content_type not in _ALLOWED_CONTENT_TYPES[bucket]:
        raise HTTPException(
            status_code=400, detail=f"Unsupported file type for {bucket}: {sorted(_ALLOWED_CONTENT_TYPES[bucket])}"
        )
    data = await file.read()
    max_bytes = _MAX_UPLOAD_BYTES[bucket]
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large (max {max_bytes // (1024 * 1024)} MB)")

    object_name = f"{user.id}/{uuid.uuid4().hex}-{file.filename or 'upload'}"
    try:
        internal_client.put_object(
            bucket, object_name, io.BytesIO(data), length=len(data), content_type=file.content_type
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}") from exc
    return {"bucket": bucket, "object_name": object_name, "url": f"/storage/public/{bucket}/{object_name}"}


def _stream_object(resp):
    try:
        yield from resp.stream(32 * 1024)
    finally:
        resp.close()
        resp.release_conn()


@router.get("/public/{bucket}/{object_name:path}")
async def get_public_file(bucket: str, object_name: str) -> StreamingResponse:
    """Unauthenticated read-back for `_DIRECT_BUCKETS`, proxied through this
    API rather than a presigned URL — see upload_file above for why."""
    if bucket not in _DIRECT_BUCKETS:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        resp = internal_client.get_object(bucket, object_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Not found") from exc
    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    return StreamingResponse(_stream_object(resp), media_type=content_type)
