"""Per-tutor Zoom account linking (OAuth authorization_code grant).

Each tutor connects their *own* Zoom account — there's no shared
platform-wide Zoom login. Server-to-Server OAuth apps (one shared account)
would have needed a paid Zoom plan on the account running the whole
platform; a regular "OAuth app" doesn't have that restriction, and a free
Zoom account has no time limit on 1:1 meetings (only group calls with 3+
people are capped at 40 minutes) — which is exactly what a tutor/student
lesson is.

The `state` param round-trip reuses edubridge_shared.security's JWT
create/decode (the same functions Identity uses for login tokens) instead of
a server-side session store: it's a short-lived, self-contained, signed
token carrying the tutor's id, so the callback (which Zoom's browser
redirect hits with no Authorization header) can recover *who* was
connecting without any shared state. Signed and verified with its own
dedicated `zoom_state_secret` (HS256) rather than the platform login-token
keys — calendar both mints and reads this token itself, and under RS256 the
platform's `jwt_public_key` can only verify, not sign.
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx

from edubridge_shared.security import create_token, decode_token, TokenError

from ..core.config import get_settings

_settings = get_settings()

_AUTHORIZE_URL = "https://zoom.us/oauth/authorize"
_TOKEN_URL = "https://zoom.us/oauth/token"
_USERINFO_URL = "https://api.zoom.us/v2/users/me"

_STATE_TOKEN_TYPE = "zoom_oauth_state"
_STATE_TTL = timedelta(minutes=10)


class ZoomOAuthError(Exception):
    pass


def is_configured() -> bool:
    return bool(_settings.zoom_client_id and _settings.zoom_client_secret)


_STATE_ALGORITHM = "HS256"


def make_state(tutor_id: str) -> str:
    token, _jti = create_token(
        subject=tutor_id,
        role="tutor",
        token_type=_STATE_TOKEN_TYPE,
        secret_key=_settings.zoom_state_secret,
        algorithm=_STATE_ALGORITHM,
        expires_delta=_STATE_TTL,
    )
    return token


def read_state(state: str) -> str:
    """Return the tutor id embedded in a `state` token, or raise ZoomOAuthError."""
    try:
        payload = decode_token(
            state,
            secret_key=_settings.zoom_state_secret,
            algorithm=_STATE_ALGORITHM,
            expected_type=_STATE_TOKEN_TYPE,
        )
    except TokenError as exc:
        raise ZoomOAuthError(f"Invalid or expired state: {exc}") from exc
    return payload.sub


def authorize_url(tutor_id: str) -> str:
    if not is_configured():
        raise ZoomOAuthError("Zoom is not configured on this server")
    params = {
        "response_type": "code",
        "client_id": _settings.zoom_client_id,
        "redirect_uri": _settings.zoom_redirect_uri,
        "state": make_state(tutor_id),
    }
    return f"{_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """Trade an authorization code for (access_token, refresh_token, expires_in)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                params={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": _settings.zoom_redirect_uri,
                },
                auth=(_settings.zoom_client_id, _settings.zoom_client_secret),
            )
    except httpx.HTTPError as exc:
        raise ZoomOAuthError(f"Could not reach Zoom: {exc}") from exc
    if resp.status_code >= 400:
        raise ZoomOAuthError(f"Zoom rejected the authorization code: {resp.text}")
    return resp.json()


async def refresh_access_token(refresh_token: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                params={"grant_type": "refresh_token", "refresh_token": refresh_token},
                auth=(_settings.zoom_client_id, _settings.zoom_client_secret),
            )
    except httpx.HTTPError as exc:
        raise ZoomOAuthError(f"Could not reach Zoom: {exc}") from exc
    if resp.status_code >= 400:
        raise ZoomOAuthError(f"Zoom rejected the refresh token: {resp.text}")
    return resp.json()


async def fetch_email(access_token: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError:
        return None
    if resp.status_code >= 400:
        return None
    return resp.json().get("email")


def expires_at_from(token_response: dict) -> datetime:
    expires_in = int(token_response.get("expires_in", 3600))
    return datetime.now(tz=timezone.utc) + timedelta(seconds=expires_in)
