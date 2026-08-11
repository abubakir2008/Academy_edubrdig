"""Short-TTL cache for the cms module (department-wide Redis, own logical db)."""

from __future__ import annotations

from edubridge_shared.cache import Cache

from .core.config import get_settings

_settings = get_settings()
cache = Cache(_settings.cache_redis_url)

# Public article listing has too many (type, limit, offset) combinations to
# invalidate precisely on every write — a short TTL is the whole consistency
# mechanism here instead: articles are edited rarely, and 20s of staleness
# after an edit is a fine trade for skipping the DB on every blog visit.
ARTICLES_LIST_TTL_SECONDS = 20


def articles_list_key(type_: str | None, limit: int, offset: int) -> str:
    return f"cms:articles:{type_ or '_'}:{limit}:{offset}"
