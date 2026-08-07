"""Redis-backed store for issued refresh tokens.

Enables refresh-token rotation and revocation (logout / "log out everywhere").
A refresh token is only accepted if its ``jti`` is still present for its user.
"""

from __future__ import annotations

import redis.asyncio as aioredis

from ..core.config import get_settings

_settings = get_settings()
_redis: aioredis.Redis = aioredis.from_url(_settings.redis_url, decode_responses=True)

_TTL_SECONDS = _settings.refresh_token_expire_days * 24 * 60 * 60


def _key(user_id: str, jti: str) -> str:
    return f"auth:refresh:{user_id}:{jti}"


async def store_refresh(user_id: str, jti: str) -> None:
    await _redis.set(_key(user_id, jti), "1", ex=_TTL_SECONDS)


async def is_valid_refresh(user_id: str, jti: str) -> bool:
    return await _redis.exists(_key(user_id, jti)) == 1


async def revoke_refresh(user_id: str, jti: str) -> None:
    await _redis.delete(_key(user_id, jti))


async def revoke_all(user_id: str) -> None:
    async for key in _redis.scan_iter(match=f"auth:refresh:{user_id}:*"):
        await _redis.delete(key)


async def ping() -> bool:
    try:
        return await _redis.ping()
    except Exception:  # pragma: no cover - health check only
        return False
