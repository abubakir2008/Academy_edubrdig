"""Scheduling department configuration (booking + calendar + lessons + video)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field

from edubridge_shared.config import DepartmentSettings


class Settings(DepartmentSettings):
    service_name: str = "scheduling"
    db_schema: str = "scheduling"

    # Video rooms are ephemeral state, so they live in Redis rather than a
    # table — video_redis_url (and its DB number, video_redis_db) is
    # inherited from DepartmentSettings.
    room_ttl_seconds: int = Field(default=4 * 60 * 60, alias="VIDEO_ROOM_TTL_SECONDS")
    join_token_ttl_seconds: int = Field(default=60 * 60, alias="VIDEO_JOIN_TOKEN_TTL_SECONDS")

    # Jitsi Meet powers the actual call. Defaults to the free public instance
    # (meet.jit.si) so lessons work with zero extra infrastructure/RAM on a
    # small VPS; point this at a self-hosted Jitsi stack later by changing one
    # env var, no code change needed.
    jitsi_domain: str = Field(default="meet.jit.si", alias="JITSI_DOMAIN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
