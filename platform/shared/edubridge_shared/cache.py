"""Short-TTL Redis cache for read-heavy, rarely-changing app data.

Cache-aside: callers check `get`, populate on miss with `set`, and
invalidate explicitly on writes with `delete`. Fails open like
`middleware.RedisRateLimitMiddleware` — a down Redis just means every read
falls through to Postgres as if there were no cache at all, never a broken
response.
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis


class Cache:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def _client(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def get(self, key: str) -> Any | None:
        try:
            redis = await self._client()
            raw = await redis.get(key)
        except Exception:
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            redis = await self._client()
            await redis.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception:
            pass

    async def delete(self, *keys: str) -> None:
        if not keys:
            return
        try:
            redis = await self._client()
            await redis.delete(*keys)
        except Exception:
            pass
