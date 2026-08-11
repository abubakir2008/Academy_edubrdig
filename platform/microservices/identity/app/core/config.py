"""Identity department configuration (auth + user profiles)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator

from edubridge_shared.config import DepartmentSettings, _normalize_pem


class Settings(DepartmentSettings):
    service_name: str = "identity"
    db_schema: str = "identity"

    # OAuth — native mobile flow: the app performs Apple sign-in and sends us
    # the id_token, which we verify against the provider's public keys.
    apple_client_id: str = Field(default="", alias="APPLE_CLIENT_ID")

    # RS256 signing key — identity is the ONLY department that holds this;
    # everyone (including identity itself, for verification) uses the public
    # half via the base class's `jwt_public_key`. See that field's comment.
    jwt_private_key: str = Field(default="", alias="JWT_PRIVATE_KEY")

    @field_validator("jwt_private_key", mode="after")
    @classmethod
    def _validate_jwt_private_key(cls, v: str) -> str:
        return _normalize_pem(v)

    # A burst of login attempts is the platform's single most valuable
    # brute-force target — kept separate from the general RATE_LIMIT_PER_MIN
    # (see app/main.py) so it can be much stricter without throttling normal
    # API traffic, and stays enforced even if the general limiter is off.
    auth_rate_limit_per_min: int = Field(default=10, alias="AUTH_RATE_LIMIT_PER_MIN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
