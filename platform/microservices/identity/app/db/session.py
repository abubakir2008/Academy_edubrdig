"""One async engine and session factory for the whole identity department."""

from __future__ import annotations

from edubridge_shared.database import build_engine, build_session_factory, make_get_db

from ..core.config import get_settings

_settings = get_settings()

engine = build_engine(
    _settings.database_url,
    schema=_settings.db_schema,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
)
SessionLocal = build_session_factory(engine)
get_db = make_get_db(SessionLocal)
