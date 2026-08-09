"""Reusable async SQLAlchemy plumbing for the shared PostgreSQL database.

All departments live in one database and are separated by schema. Each
department builds its ``Base`` with :func:`build_base`, which pins that
department's schema onto the metadata — so a model only ever declares
``__tablename__`` and lands in the right schema automatically.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Callable
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#: Every department's schema, in the order Alembic creates them.
DEPARTMENT_SCHEMAS = (
    "identity",
    "engagement",
    "content",
    "backoffice",
    "academics",
    "calendar",
)

# Explicit constraint naming so Alembic autogenerate produces stable names
# instead of database-assigned ones.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def build_base(schema: str) -> type[DeclarativeBase]:
    """Return a declarative base whose tables default to ``schema``."""
    metadata = MetaData(schema=schema, naming_convention=NAMING_CONVENTION)

    class Base(DeclarativeBase):
        pass

    Base.metadata = metadata
    return Base


def build_engine(
    database_url: str,
    *,
    schema: str | None = None,
    pool_size: int = 5,
    max_overflow: int = 2,
) -> AsyncEngine:
    """Async engine with a deliberately small pool.

    ``schema`` sets the connection's ``search_path`` so unqualified names (raw
    SQL, ``func`` calls) resolve inside the department's schema first.
    """
    connect_args: dict[str, object] = {}
    if schema:
        connect_args["server_settings"] = {"search_path": f"{schema},public"}
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=1800,
        future=True,
        connect_args=connect_args,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def make_get_db(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """Return a FastAPI dependency that yields a session per request."""

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    return get_db
