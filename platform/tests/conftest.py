"""Shared pytest fixtures for the department test suites.

Runs against a real Postgres (each department gets its own throwaway schema,
created from its SQLAlchemy metadata and dropped after the test module) and a
real Redis. This intentionally does not mock the database: the bugs this
suite exists to catch — the reviews unique-constraint hole, the wallet
double-credit race, silently-missing calendar enforcement — are exactly the
kind that a mocked session hides.

Point ``TEST_DATABASE_URL`` / ``TEST_REDIS_URL`` at a running stack (e.g.
``docker compose up -d postgres redis``) to run these locally; CI should do
the same before invoking pytest.
"""

from __future__ import annotations

import os
import sys
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg
import httpx
import jwt
import pytest
import pytest_asyncio

JWT_SECRET = "test-secret-do-not-use-in-prod"
JWT_ALGORITHM = "HS256"

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://edubridge:edubridge@localhost:5432/edubridge"
)
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15")

MICROSERVICES = Path(__file__).resolve().parent.parent / "microservices"


def mint_access_token(user_id: str, role: str) -> str:
    """A hand-rolled token, independent of edubridge_shared.security.

    Deliberately doesn't import the app's own token code — a test that used
    the same encoder to both mint and verify tokens couldn't catch a bug in
    that encoder.
    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


#: A dedicated Redis logical DB for every purpose a department uses one for,
#: all far away from the DBs (0-4) a real dev/prod stack reads and writes.
#: Every test that exercises an endpoint which publishes an event (reviews,
#: bookings, payments, ...) does a REAL bus.publish() — there is no mock here
#: — so without this, test runs leave stale, permanently-unacked messages in
#: whatever Redis a developer's `docker compose up` is also pointed at.
_TEST_REDIS_DB = "15"


def _department_env(department: str, schema: str) -> dict[str, str]:
    # Honor POSTGRES_HOST / REDIS_HOST from the real environment (the tests
    # run inside the compose network in CI, where the hostname is "postgres"
    # / "redis", not localhost) — only fall back to localhost for a bare
    # `pytest` invocation against a port-forwarded stack.
    return {
        "JWT_SECRET_KEY": JWT_SECRET,
        "JWT_ALGORITHM": JWT_ALGORITHM,
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "POSTGRES_USER": "edubridge",
        "POSTGRES_PASSWORD": "edubridge",
        "POSTGRES_DB": "edubridge",
        "REDIS_HOST": os.getenv("REDIS_HOST", "localhost"),
        "REDIS_DB": _TEST_REDIS_DB,
        "VIDEO_REDIS_DB": _TEST_REDIS_DB,
        "RATE_LIMIT_REDIS_DB": _TEST_REDIS_DB,
        "REALTIME_REDIS_DB": _TEST_REDIS_DB,
        "EVENTS_REDIS_DB": _TEST_REDIS_DB,
        "EMAIL_ENABLED": "false",
        "RATE_LIMIT_PER_MIN": "0",
    }


@pytest_asyncio.fixture
async def department_app(request):
    """Import one department's FastAPI app against a fresh throwaway schema.

    ``request.param`` is the department name (e.g. "identity"). Each test
    using this fixture gets its own schema (``<department>_test_<uuid>``) so
    parallel test modules never see each other's rows, and the schema is
    dropped afterward regardless of test outcome.
    """
    department = request.param
    schema = f"{department}_test_{uuid.uuid4().hex[:8]}"

    for key, value in _department_env(department, schema).items():
        os.environ[key] = value
    os.environ["DB_SCHEMA_OVERRIDE"] = schema  # read by the monkeypatch below

    dept_root = str(MICROSERVICES / department)
    sys.path.insert(0, dept_root)

    # Every department's get_settings() is @lru_cache'd; a bare import would
    # reuse a stale instance across tests. Clear the whole app import graph so
    # each test gets settings pointing at *this* test's schema.
    for name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[name]

    import importlib

    from edubridge_shared import config as shared_config

    original_init = shared_config.DepartmentSettings.__init__

    def patched_init(self, **kwargs):
        original_init(self, **kwargs)
        self.db_schema = schema

    shared_config.DepartmentSettings.__init__ = patched_init
    try:
        main = importlib.import_module("app.main")
    finally:
        shared_config.DepartmentSettings.__init__ = original_init

    from app.db.base import Base
    from app.db.session import engine as dept_engine

    async with dept_engine.begin() as conn:
        await conn.execute(_create_schema_ddl(schema))
        await conn.run_sync(Base.metadata.create_all)

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield main, client

    async with dept_engine.begin() as conn:
        await conn.execute(_drop_schema_ddl(schema))
    await dept_engine.dispose()

    sys.path.remove(dept_root)


def _create_schema_ddl(schema: str):
    from sqlalchemy import text

    return text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')


def _drop_schema_ddl(schema: str):
    from sqlalchemy import text

    return text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _require_postgres() -> AsyncIterator[None]:
    """Fail fast with a clear message if Postgres isn't reachable."""
    try:
        conn = await asyncpg.connect(TEST_DATABASE_URL)
        await conn.close()
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.exit(
            f"Postgres not reachable at {TEST_DATABASE_URL} — start it with "
            f"`docker compose up -d postgres redis` before running these tests "
            f"({exc})"
        )
    yield
