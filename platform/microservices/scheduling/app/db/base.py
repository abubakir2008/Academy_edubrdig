"""Declarative base for the scheduling department.

Every model in this department lands in the ``scheduling`` PostgreSQL schema,
because the base's metadata carries that schema.
"""

from __future__ import annotations

from edubridge_shared.database import build_base

from ..core.config import get_settings

Base = build_base(get_settings().db_schema)
