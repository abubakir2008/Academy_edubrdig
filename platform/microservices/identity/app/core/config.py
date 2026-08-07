"""Identity department configuration (auth + user profiles)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field

from edubridge_shared.config import DepartmentSettings


class Settings(DepartmentSettings):
    service_name: str = "identity"
    db_schema: str = "identity"

    # OAuth — native mobile flow: the app performs Google/Apple sign-in and
    # sends us the id_token, which we verify against the provider's public keys.
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    apple_client_id: str = Field(default="", alias="APPLE_CLIENT_ID")


@lru_cache
def get_settings() -> Settings:
    return Settings()
