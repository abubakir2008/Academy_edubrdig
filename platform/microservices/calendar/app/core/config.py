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

    # --- Lesson recordings (LiveKit auto-egress → an S3-compatible bucket,
    # e.g. Cloudflare R2) --- LiveKit Cloud's egress workers run on LiveKit's
    # own infrastructure and upload the finished file directly to this
    # bucket -- this department never touches the video bytes, only mints
    # presigned URLs to read them back. Empty by default: lessons still work
    # without recording, they're just never recorded.
    recordings_s3_endpoint: str = Field(default="", alias="RECORDINGS_S3_ENDPOINT")
    recordings_s3_access_key: str = Field(default="", alias="RECORDINGS_S3_ACCESS_KEY")
    recordings_s3_secret_key: str = Field(default="", alias="RECORDINGS_S3_SECRET_KEY")
    recordings_s3_bucket: str = Field(default="", alias="RECORDINGS_S3_BUCKET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
