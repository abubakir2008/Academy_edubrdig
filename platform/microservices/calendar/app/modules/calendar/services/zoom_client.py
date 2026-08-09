"""Zoom Meeting API — create/update/delete a meeting for a lesson, keeping
the tutor's stored OAuth token fresh along the way.

One meeting per lesson instance (not one per recurring series) — a
deliberate choice, see the courses/calendar feature plan.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import zoom_account as zoom_account_crud
from ..models.zoom_account import ZoomAccount
from . import zoom_oauth

_API_BASE = "https://api.zoom.us/v2"
#: Refresh a bit before actual expiry so a slow request never lands mid-flight
#: with a token that expires between the refresh check and the API call.
_REFRESH_MARGIN = timedelta(minutes=2)


class ZoomError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


async def ensure_fresh_token(db: AsyncSession, account: ZoomAccount) -> str:
    if datetime.now(tz=timezone.utc) < account.token_expires_at - _REFRESH_MARGIN:
        return account.access_token
    try:
        token_response = await zoom_oauth.refresh_access_token(account.refresh_token)
    except zoom_oauth.ZoomOAuthError as exc:
        raise ZoomError(f"Could not refresh the teacher's Zoom token: {exc}") from exc
    # Zoom rotates the refresh token on every use — the old one is invalid
    # the moment a new one is issued, so this must be persisted immediately.
    await zoom_account_crud.save_tokens(
        db,
        account,
        access_token=token_response["access_token"],
        refresh_token=token_response["refresh_token"],
        token_expires_at=zoom_oauth.expires_at_from(token_response),
    )
    return token_response["access_token"]


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def create_meeting(access_token: str, *, topic: str, start: datetime, duration_minutes: int) -> dict:
    payload = {
        "topic": topic,
        "type": 2,  # scheduled (non-recurring) meeting
        "start_time": _iso(start),
        "duration": duration_minutes,
        "timezone": "UTC",
        "settings": {"join_before_host": True, "waiting_room": False},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{_API_BASE}/users/me/meetings",
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise ZoomError(f"Could not reach Zoom: {exc}") from exc
    if resp.status_code >= 400:
        raise ZoomError(f"Zoom could not create the meeting: {resp.text}")
    body = resp.json()
    return {"id": str(body["id"]), "join_url": body["join_url"], "start_url": body["start_url"]}


async def update_meeting(access_token: str, meeting_id: str, *, start: datetime, duration_minutes: int) -> None:
    payload = {"start_time": _iso(start), "duration": duration_minutes, "timezone": "UTC"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"{_API_BASE}/meetings/{meeting_id}",
                json=payload,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise ZoomError(f"Could not reach Zoom: {exc}") from exc
    if resp.status_code >= 400:
        raise ZoomError(f"Zoom could not update the meeting: {resp.text}")


async def delete_meeting(access_token: str, meeting_id: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(
                f"{_API_BASE}/meetings/{meeting_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise ZoomError(f"Could not reach Zoom: {exc}") from exc
    # 404 means it's already gone (e.g. the tutor deleted it from the Zoom
    # app directly) — that's fine, our own delete is still a success.
    if resp.status_code >= 400 and resp.status_code != 404:
        raise ZoomError(f"Zoom could not delete the meeting: {resp.text}")
