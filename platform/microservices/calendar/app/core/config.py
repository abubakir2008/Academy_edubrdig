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

    # --- Zoom (per-tutor OAuth — see modules/calendar/services/zoom_oauth.py) ---
    #: Empty by default: no meetings can be created until a real Zoom OAuth
    #: app is registered (marketplace.zoom.us) and these are set.
    zoom_client_id: str = Field(default="", alias="ZOOM_CLIENT_ID")
    zoom_client_secret: str = Field(default="", alias="ZOOM_CLIENT_SECRET")
    #: Must exactly match the redirect URI configured on the Zoom app.
    zoom_redirect_uri: str = Field(
        default="http://localhost/api/calendar/zoom/callback", alias="ZOOM_REDIRECT_URI"
    )
    #: Where the OAuth callback sends the browser back to once linking is done.
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # The Zoom-link CSRF `state` param is signed AND verified entirely within
    # this department (see services/zoom_oauth.py) — it was previously reusing
    # the platform-wide `jwt_secret_key`/`jwt_algorithm`, but under RS256 that
    # pair now means "verify-only public key", which can't sign anything.
    # It was never really a login credential anyway, so it gets its own
    # dedicated symmetric secret instead of borrowing the login token's keys.
    zoom_state_secret: str = Field(default="", alias="ZOOM_STATE_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()
