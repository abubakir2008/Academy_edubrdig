"""Backoffice department configuration (admin + analytics)."""

from __future__ import annotations

from functools import lru_cache

from edubridge_shared.config import DepartmentSettings


class Settings(DepartmentSettings):
    service_name: str = "backoffice"
    db_schema: str = "backoffice"


@lru_cache
def get_settings() -> Settings:
    return Settings()
