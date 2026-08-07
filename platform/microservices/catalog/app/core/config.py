"""Catalog department configuration (tutors + students + search)."""

from __future__ import annotations

from functools import lru_cache

from edubridge_shared.config import DepartmentSettings


class Settings(DepartmentSettings):
    service_name: str = "catalog"
    db_schema: str = "catalog"


@lru_cache
def get_settings() -> Settings:
    return Settings()
