"""Short-TTL cache for the courses module (department-wide Redis, own logical db)."""

from __future__ import annotations

from edubridge_shared.cache import Cache

from .core.config import get_settings

_settings = get_settings()
cache = Cache(_settings.cache_redis_url)

MY_COURSES_TTL_SECONDS = 60


def my_courses_key(user_id: object) -> str:
    return f"courses:me:{user_id}"
