"""Shared pytest fixtures for the department test suites.

Runs against a real Postgres (each department gets its own throwaway schema,
created from its SQLAlchemy metadata and dropped after the test module) and a
real Redis. This intentionally does not mock the database: the bugs this
suite exists to catch are exactly the kind that a mocked session hides.

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

JWT_ALGORITHM = "RS256"
#: Pinned rather than left unset: a developer's real `platform/.env` (not
#: read by these tests directly, but `docker compose run` still passes its
#: own environment through to the container) may already define a real
#: INTERNAL_SECRET, which would make `require_internal` start rejecting
#: internal-only test calls that assume the guard is a no-op. Explicit beats
#: "depends on what's in someone's .env", same reasoning as the LIVEKIT_*
#: vars below.
TEST_INTERNAL_SECRET = "test-internal-secret-do-not-use-in-prod"

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql://edubridge:edubridge@localhost:5432/edubridge"
)
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/15")

MICROSERVICES = Path(__file__).resolve().parent.parent / "microservices"

# Every department verifies with the public key alone (see
# edubridge_shared.config's DepartmentSettings docstring on why: RS256 means
# compromising one department's public key can't forge tokens for another).
# `mint_access_token` below signs with the matching private key, same as
# identity's real `create_access_token` would.
#
# Hardcoded (not generated fresh at import time, e.g. via
# `rsa.generate_private_key`): this module ends up imported twice under two
# different names in the same process — once as `tests.conftest` (test files
# do `from tests.conftest import mint_access_token`) and once as pytest's own
# auto-discovered `conftest` (which is where the `department_app` fixture
# actually gets resolved from). Two separate module objects means two
# separate copies of any module-level state; a freshly-*generated* keypair
# would make each copy mint/verify against a *different* key, so a token
# minted via the `tests.conftest` import would fail to verify against the
# `department_app` fixture's env (which comes from the other copy) — exactly
# the "Invalid token" failure that motivated pinning this. A hardcoded
# literal is identical in both copies, same as the old hardcoded HS256
# secret string this replaced. Test-only key, never used for anything real.
JWT_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDT/ujVQGqdQbW+
kVnOWIT0zVztWLBInG9FeoFX6QYCcqNbqrxDv9/C6wl9+J2RFRyJjLn4DVxc3xg3
Wrh8QoPwEVzmuOpuMeoMtFUvcnHirOYUtr+ycNX0W+Gwu7rW0pra5v/qZdxcLqTP
47sNlwHITs1fUuGMDVdfsToP2Ke61S7XbWUO5jbc2PIAdyrxlR8WMnfAqyUeVm3T
IIcs16HXsBvkoO3B2reN0UjciuCkvzYt2QQBet/4F6nrEhIRrMPR92v2+xzNjJD9
l73w+H9LMrL0+3J/QZkd8ykP4v8LtLvbTdWdoCnpoDAUMn1i/ccBGlsRYBaYPm0M
mqNTmr2vAgMBAAECggEAC1iLtooViqgPJY1a7JfBOebZz9wcxy4UKHhHfuB6UVw4
UPogzFFzFNgGcIcDS9YA6n2tIFD6vf+0qJXC5OecbxdGzRRde5tRRu/J1Vm/LZ4K
TFaBiPfQA519RTuu4rtvzUJqtO1Rr19Rs8yg4LfRwRoylKT3bEr0f6sZC+sRAwc3
y8zFPggld5QhHUcz14cJ37Huq8Utdt+9eNvZGHHZ2EQr50yUABcIgoQYsQRg69KE
uUox3XSc9OUTABj4yjslpMuO9/5xqBPtP0xIU/awATLppyFCF3NiuBqpVeasYob2
99EA/BrpbBDwmKzhOCowVjoGPAI+Wxya7TYe4ckWgQKBgQD+UqlkfF4MwqxNUDQz
nPiSoKJ+1RWMoEDxZ/x5bAKi7ytkGXcVAJl4qsJLImKbKWjPFooXK37iglLe1wS4
p51GK4nCA+ZO7O/vJv6B2m7lVNsmxOI9xypNSb2E+IAgzCkGq/sspkGstg985xKo
EMvKpHsdY95wpGGSYGki0gb8LwKBgQDVZMru0IrBbFmgGN1S4A+VIKgkAQRV43vT
An3LPcCTK/TsFy4hi++RB5SdOxUwoSYeaRh3R7w+KXWJoiiniBACyBjMP9U41mM9
uI/+JByii+WzFiiEVQN3zdT5jc5bOQ+YOacMAD6XjRfb5PFGjmpw0V++3ILmHkVL
heiU6ah2gQKBgQDOUOTWfgYWN/9roPsYO+lzmhj454hZ0s+ch41MO5FP+NKsm/P8
98WJHI4OQdDYqxk5lsFj1odS3gK4gJp16pQuDrfsyxkVQiXLT0j8suVv6gz3QJWB
JIdut7mlm6rl8Hn/zZkwOZfhsriRzStXaHjK5fBygUg8/T2ib9AazWOZRQKBgQC/
yiUx2rC7AzzSTUauM78NkxpLsbZJ03j4v2Z8AnZQT9ODVZoagIDCYoPJhM6YtF1k
O6THn+uqGu0O1HWhjQKG3XycJkrnGJh9YqHYEnDCDuZVvPaRaS8CwDZITJFJH9HK
SRbADIA1CZSGCBBqD5nO5/8btWjYliBFrobJP/AvAQKBgQCGBN2q7Y/tOQdIX68B
NQFpR9/QaahKOsYA+T1KjvvxVAdqMF5c8WNo/NZ58brOOJmA6OGxSxYKIJ70s+Kn
xi/9LI8wywm2JS2ops8kxd/QpqO9OQrHynijSfiPn+A0+IF2cnqla1A3WtR7MHNP
aDy1ofC/HHb2+qyzg7E5G9HHXw==
-----END PRIVATE KEY-----
"""
JWT_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0/7o1UBqnUG1vpFZzliE
9M1c7ViwSJxvRXqBV+kGAnKjW6q8Q7/fwusJffidkRUciYy5+A1cXN8YN1q4fEKD
8BFc5rjqbjHqDLRVL3Jx4qzmFLa/snDV9FvhsLu61tKa2ub/6mXcXC6kz+O7DZcB
yE7NX1LhjA1XX7E6D9inutUu121lDuY23NjyAHcq8ZUfFjJ3wKslHlZt0yCHLNeh
17Ab5KDtwdq3jdFI3IrgpL82LdkEAXrf+Bep6xISEazD0fdr9vsczYyQ/Ze98Ph/
SzKy9Ptyf0GZHfMpD+L/C7S7203VnaAp6aAwFDJ9Yv3HARpbEWAWmD5tDJqjU5q9
rwIDAQAB
-----END PUBLIC KEY-----
"""


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
    return jwt.encode(payload, JWT_PRIVATE_KEY_PEM, algorithm=JWT_ALGORITHM)


#: A dedicated Redis logical DB for every purpose a department uses one for,
#: all far away from the DBs (0-4) a real dev/prod stack reads and writes.
#: Every test that exercises an endpoint which publishes an event does a REAL
#: bus.publish() — there is no mock here — so without this, test runs leave
#: stale, permanently-unacked messages in whatever Redis a developer's
#: `docker compose up` is also pointed at.
_TEST_REDIS_DB = "15"


def _department_env(department: str, schema: str) -> dict[str, str]:
    # Honor POSTGRES_HOST / REDIS_HOST from the real environment (the tests
    # run inside the compose network in CI, where the hostname is "postgres"
    # / "redis", not localhost) — only fall back to localhost for a bare
    # `pytest` invocation against a port-forwarded stack.
    return {
        # Public key for verification (every department); private key too —
        # harmless for every department except identity, which is the only
        # one whose Settings subclass actually has a field for it and uses
        # it to mint tokens in `POST /auth/login` etc.
        "JWT_PUBLIC_KEY": JWT_PUBLIC_KEY_PEM,
        "JWT_PRIVATE_KEY": JWT_PRIVATE_KEY_PEM,
        "JWT_ALGORITHM": JWT_ALGORITHM,
        "INTERNAL_SECRET": TEST_INTERNAL_SECRET,
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "POSTGRES_USER": "edubridge",
        "POSTGRES_PASSWORD": "edubridge",
        "POSTGRES_DB": "edubridge",
        "REDIS_HOST": os.getenv("REDIS_HOST", "localhost"),
        "REDIS_DB": _TEST_REDIS_DB,
        "RATE_LIMIT_REDIS_DB": _TEST_REDIS_DB,
        "REALTIME_REDIS_DB": _TEST_REDIS_DB,
        "EVENTS_REDIS_DB": _TEST_REDIS_DB,
        "EMAIL_ENABLED": "false",
        "PUSH_ENABLED": "false",
        "RATE_LIMIT_PER_MIN": "0",
        # Only calendar's Settings has fields for these — harmless no-ops for
        # every other department. Real values (not a Zoom-style OAuth dance)
        # so calendar's join-token test can mint and verify a real token
        # instead of mocking anything.
        "LIVEKIT_URL": "wss://test.livekit.cloud",
        "LIVEKIT_API_KEY": "test-key",
        "LIVEKIT_API_SECRET": "test-secret-32-bytes-long-enough!!",
    }


async def _boot_department(department: str):
    """Import one department's FastAPI app against a fresh throwaway schema
    and create its tables. Returns ``(main_module, engine, schema)``.

    Each caller gets its own schema (``<department>_test_<uuid>``) so
    parallel test modules never see each other's rows. ``dept_root`` is
    removed from ``sys.path`` again immediately after import — leaving two
    departments' roots on the path at once (this helper is also what makes
    booting *two* departments in one test process possible, see
    ``test_calendar_lessons.py``) would let Python resolve the shared ``app``
    package name to the wrong department on the next department's import.
    """
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
        sys.path.remove(dept_root)

    from app.db.base import Base
    from app.db.session import engine as dept_engine

    async with dept_engine.begin() as conn:
        await conn.execute(_create_schema_ddl(schema))
        await conn.run_sync(Base.metadata.create_all)

    return main, dept_engine, schema


async def _drop_department(engine, schema: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(_drop_schema_ddl(schema))
    await engine.dispose()


@pytest_asyncio.fixture
async def department_app(request):
    """Import one department's FastAPI app against a fresh throwaway schema.

    ``request.param`` is the department name (e.g. "identity").
    """
    main, dept_engine, schema = await _boot_department(request.param)

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield main, client

    await _drop_department(dept_engine, schema)


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
