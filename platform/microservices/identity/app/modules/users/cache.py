"""Short-TTL cache for the users module (department-wide Redis, own logical db)."""

from __future__ import annotations

from edubridge_shared.cache import Cache

from .core.config import get_settings

_settings = get_settings()
cache = Cache(_settings.cache_redis_url)

PROFILE_TTL_SECONDS = 90


def profile_key(user_id: object) -> str:
    return f"profile:{user_id}"
