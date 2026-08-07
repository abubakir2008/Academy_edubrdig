"""Storage endpoints (namespaced under /storage) backed by MinIO."""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from edubridge_shared.fastapi_auth import CurrentUser

from ...core.config import get_settings
from ...storage import public_client as client
from ..deps import get_current_user

router = APIRouter(prefix="/storage", tags=["storage"])
_settings = get_settings()
_ALLOWED = {b.strip() for b in _settings.default_buckets.split(",")}


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
    try:
        url = client.presigned_get_object(
            payload.bucket, payload.object_name, expires=timedelta(seconds=payload.expires_seconds)
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Storage unavailable: {exc}") from exc
    return {"download_url": url, "bucket": payload.bucket, "object_name": payload.object_name}
