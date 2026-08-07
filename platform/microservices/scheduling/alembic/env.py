"""Alembic environment for the scheduling department.

Runs migrations against the scheduling schema only, inside the one shared
platform database. ``version_table_schema`` keeps this department's applied-
revision bookkeeping inside its own schema too, so departments never contend
over Alembic's version table.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base

# Import every model module so Base.metadata is fully populated before
# autogenerate or upgrade runs.
import app.modules.booking.models.booking  # noqa: F401
import app.modules.calendar.models.calendar  # noqa: F401
import app.modules.lessons.models.lesson  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_settings = get_settings()
config.set_main_option("sqlalchemy.url", _settings.sync_database_url)

target_metadata = Base.metadata
SCHEMA = _settings.db_schema


def run_migrations_offline() -> None:
    context.configure(
        url=_settings.sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        version_table_schema=SCHEMA,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    connection.execute(_create_schema_sql())
    connection.execute(_set_search_path_sql())
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _create_schema_sql():
    from sqlalchemy import text

    return text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")


def _set_search_path_sql():
    from sqlalchemy import text

    return text(f"SET search_path TO {SCHEMA}, public")


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": _settings.database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.begin() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
