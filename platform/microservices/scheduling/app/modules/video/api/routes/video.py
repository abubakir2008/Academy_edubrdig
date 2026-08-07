"""Video call room endpoints (namespaced under /video), state in Redis.

Issues signed join tokens a WebRTC/SFU frontend can present. The media layer
itself (e.g. LiveKit / mediasoup) validates these tokens; here we own room
lifecycle + access control.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import jwt
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from edubridge_shared.fastapi_auth import CurrentUser

from ...core.config import get_settings
from ..deps import get_current_user

router = APIRouter(prefix="/video", tags=["video"])
_settings = get_settings()
# Video rooms are ephemeral, so they get their own Redis logical DB rather than
# sharing the department's default (which auth-adjacent code may flush/scan).
_redis = aioredis.from_url(_settings.video_redis_url, decode_responses=True)


class CreateRoom(BaseModel):
    lesson_id: str


def _room_key(room_id: str) -> str:
    return f"video:room:{room_id}"


def _join_url(room_id: str, user: CurrentUser) -> str:
    # meet.jit.si rooms are unauthenticated — reachability of this exact,
    # random room name *is* the access control, matching the join_token's
    # role for a real SFU. displayName pre-fills the on-screen name.
    display = quote(user.role.replace("_", " ").title())
    return f"https://{_settings.jitsi_domain}/EduBridge-{room_id}#userInfo.displayName=%22{display}%22"


def _issue_join_token(room_id: str, user: CurrentUser) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "room_id": room_id,
        "sub": user.id,
        "role": user.role,
        "type": "video",
        "iat": now,
        "exp": now + timedelta(seconds=_settings.join_token_ttl_seconds),
    }
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)


@router.post("/rooms", status_code=201)
async def create_room(
    payload: CreateRoom, user: CurrentUser = Depends(get_current_user)
) -> dict:
    # One stable room per lesson.
    mapping_key = f"video:lesson:{payload.lesson_id}"
    room_id = await _redis.get(mapping_key)
    if room_id is None:
        room_id = uuid.uuid4().hex
        room = {
            "room_id": room_id,
            "lesson_id": payload.lesson_id,
            "created_by": user.id,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        await _redis.set(_room_key(room_id), json.dumps(room), ex=_settings.room_ttl_seconds)
        await _redis.set(mapping_key, room_id, ex=_settings.room_ttl_seconds)
    return {"room_id": room_id, "token": _issue_join_token(room_id, user), "join_url": _join_url(room_id, user)}


@router.post("/rooms/{room_id}/join")
async def join_room(room_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    raw = await _redis.get(_room_key(room_id))
    if raw is None:
        raise HTTPException(status_code=404, detail="Room not found or expired")
    return {"room_id": room_id, "token": _issue_join_token(room_id, user), "join_url": _join_url(room_id, user)}


@router.get("/rooms/{room_id}")
async def get_room(room_id: str, _: CurrentUser = Depends(get_current_user)) -> dict:
    raw = await _redis.get(_room_key(room_id))
    if raw is None:
        raise HTTPException(status_code=404, detail="Room not found or expired")
    return json.loads(raw)
