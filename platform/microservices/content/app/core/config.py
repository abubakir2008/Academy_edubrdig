"""Content department configuration (cms + localization + ai + storage)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field

from edubridge_shared.config import DepartmentSettings


class Settings(DepartmentSettings):
    service_name: str = "content"
    db_schema: str = "content"

    # --- Study-aid generation (see modules/ai) ---
    #: Per-user daily request cap (the admin-configurable "AI Limits" in the TZ).
    ai_daily_limit: int = Field(default=100, alias="AI_DAILY_LIMIT")
    #: With no key set, the module answers from local templates and says so.
    #: Anthropic wins if both are set — see modules/ai/services/engine.py.
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-5", alias="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=1024, alias="ANTHROPIC_MAX_TOKENS")
    #: Free-tier alternative for local/test use — aistudio.google.com, no card required.
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    # "-latest" alias tracks whatever Google currently recommends — pinned
    # dated versions (e.g. gemini-2.5-flash) get deprecated for new API keys
    # within months, so a fixed default here would keep going stale.
    gemini_model: str = Field(default="gemini-flash-latest", alias="GEMINI_MODEL")

    # --- Object storage ---
    minio_host: str = Field(default="minio", alias="MINIO_HOST")
    minio_port: int = Field(default=9000, alias="MINIO_PORT")
    minio_access_key: str = Field(default="edubridge", alias="MINIO_ROOT_USER")
    minio_secret_key: str = Field(default="edubridge123", alias="MINIO_ROOT_PASSWORD")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # Presigned URLs are handed to a browser, which can't resolve the internal
    # Docker hostname above — they must carry whatever host/port the browser
    # itself can reach (localhost:9000 in dev; the real domain behind a
    # reverse proxy in production).
    minio_public_endpoint: str = Field(default="localhost:9000", alias="MINIO_PUBLIC_ENDPOINT")

    #: Buckets created on startup (avatars, certificates, materials, videos, docs, chat).
    default_buckets: str = "avatars,certificates,materials,videos,documents,chat"

    @property
    def minio_endpoint(self) -> str:
        return f"{self.minio_host}:{self.minio_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
