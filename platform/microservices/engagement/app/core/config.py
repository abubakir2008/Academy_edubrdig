"""Engagement department configuration (chat + notifications + reviews + support)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field

from edubridge_shared.config import DepartmentSettings


class Settings(DepartmentSettings):
    service_name: str = "engagement"
    db_schema: str = "engagement"

    # Email (SMTP). Defaults target the local MailHog catcher.
    email_enabled: bool = Field(default=True, alias="EMAIL_ENABLED")
    smtp_host: str = Field(default="mailhog", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="EduBridge <no-reply@edubridge.local>", alias="SMTP_FROM")
    smtp_tls: bool = Field(default=False, alias="SMTP_TLS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
