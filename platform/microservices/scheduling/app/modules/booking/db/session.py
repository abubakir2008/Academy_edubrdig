"""Database session for the booking module (department-wide engine)."""

from __future__ import annotations

from ....db.session import SessionLocal, engine, get_db

__all__ = ["SessionLocal", "engine", "get_db"]
