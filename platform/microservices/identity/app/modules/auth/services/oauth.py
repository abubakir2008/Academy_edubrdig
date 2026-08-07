"""Verify Google / Apple id_tokens (native mobile sign-in flow).

The mobile app runs the native Google/Apple sign-in and sends us the resulting
``id_token``. We verify its signature against the provider's published public
keys and its audience against our client id, then trust the ``email``/``sub``.
"""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

from ..core.config import get_settings

_settings = get_settings()

_GOOGLE_CERTS = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISS = ("https://accounts.google.com", "accounts.google.com")
_APPLE_CERTS = "https://appleid.apple.com/auth/keys"
_APPLE_ISS = "https://appleid.apple.com"

_google_jwks = PyJWKClient(_GOOGLE_CERTS)
_apple_jwks = PyJWKClient(_APPLE_CERTS)


class OAuthError(Exception):
    pass


def _verify(id_token: str, jwks: PyJWKClient, audience: str, issuer) -> dict:
    if not audience:
        raise OAuthError("Provider is not configured on this server")
    try:
        key = jwks.get_signing_key_from_jwt(id_token).key
        return jwt.decode(id_token, key, algorithms=["RS256"], audience=audience, issuer=issuer)
    except jwt.PyJWTError as exc:
        raise OAuthError(f"Invalid id_token: {exc}") from exc


def verify_google(id_token: str) -> tuple[str, str]:
    """Return ``(subject, email)`` for a valid Google id_token."""
    claims = _verify(id_token, _google_jwks, _settings.google_client_id, list(_GOOGLE_ISS))
    email = claims.get("email")
    if not email:
        raise OAuthError("Google token has no email")
    return claims["sub"], email


def verify_apple(id_token: str) -> tuple[str, str]:
    claims = _verify(id_token, _apple_jwks, _settings.apple_client_id, _APPLE_ISS)
    email = claims.get("email")
    if not email:
        raise OAuthError("Apple token has no email")
    return claims["sub"], email
