"""Declarative base for the academics department."""

from __future__ import annotations

from edubridge_shared.database import build_base

from ..core.config import get_settings

Base = build_base(get_settings().db_schema)
