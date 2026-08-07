"""JWT creation / verification shared by all services.

The Auth Service issues tokens; every other service only needs to *verify*
them. Both live here so the claim format can never drift between services.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired or has a wrong type."""


@dataclass(frozen=True)
class TokenPayload:
    sub: str  # user id
    role: str
    type: str
    jti: str
    exp: int


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_token(
    *,
    subject: str,
    role: str,
    token_type: str,
    secret_key: str,
    algorithm: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Return ``(encoded_jwt, jti)``.

    The ``jti`` is returned so the caller (Auth Service) can persist / revoke
    refresh tokens in Redis.
    """
    jti = uuid.uuid4().hex
    issued_at = _now()
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": issued_at,
        "exp": issued_at + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    encoded = jwt.encode(payload, secret_key, algorithm=algorithm)
    return encoded, jti


def decode_token(
    token: str,
    *,
    secret_key: str,
    algorithm: str,
    expected_type: str | None = None,
) -> TokenPayload:
    """Decode and validate a token, raising :class:`TokenError` on any problem."""
    try:
        # ``leeway`` tolerates small clock skew between services (e.g. a Docker
        # VM clock lagging the host) so freshly-issued tokens aren't rejected.
        raw = jwt.decode(token, secret_key, algorithms=[algorithm], leeway=120)
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid token") from exc

    token_type = raw.get("type")
    if expected_type is not None and token_type != expected_type:
        raise TokenError(f"Expected {expected_type} token, got {token_type!r}")

    try:
        return TokenPayload(
            sub=str(raw["sub"]),
            role=str(raw["role"]),
            type=str(raw["type"]),
            jti=str(raw["jti"]),
            exp=int(raw["exp"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise TokenError("Token is missing required claims") from exc
