"""Calendar department configuration (advanced scheduling for courses)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field

from edubridge_shared.config import DepartmentSettings


class Settings(DepartmentSettings):
    service_name: str = "calendar"
    db_schema: str = "calendar"

    #: Upper bound on how many weekly instances a single recurring-lesson
    #: request can generate, so one bad request can't flood the schema.
    max_recurrence_weeks: int = Field(default=26, alias="MAX_RECURRENCE_WEEKS")

    # --- LiveKit (in-app video calls — see modules/calendar/services/livekit_client.py) ---
    #: The room-service/WebSocket endpoint the *client* connects to, e.g.
    #: `wss://your-project.livekit.cloud` for LiveKit Cloud, or your own
    #: self-hosted server's URL. Handed back verbatim in the join response —
    #: the frontend has no LiveKit config of its own.
    livekit_url: str = Field(default="", alias="LIVEKIT_URL")
    #: Empty by default: joining fails with a clear "not configured" error
    #: until a real LiveKit project's key/secret are set (cloud.livekit.io,
    #: or your own server's generated keys if self-hosting).
    livekit_api_key: str = Field(default="", alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(default="", alias="LIVEKIT_API_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
