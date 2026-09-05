"""Settings shared by every department service.

The platform runs as a handful of **departments** (identity, engagement,
content, backoffice). They all share one
PostgreSQL database and one Redis; a department is isolated by its own
PostgreSQL **schema** rather than its own database, which keeps the connection
and memory footprint small enough for a 4 GB host.

A concrete department subclasses :class:`DepartmentSettings`, sets
``service_name`` and ``db_schema``, and adds only the extra fields its own
modules need.
"""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_pem(value: str) -> str:
    """PEM keys live in `.env` as a single line with literal ``\\n`` escapes
    (real multi-line values are awkward in a `.env` file) — turn them back
    into real newlines before anything tries to parse them as a key."""
    return value.replace("\\n", "\n")

# Redis logical database allocation, so features never clobber each other.
REDIS_DB_TOKENS = 0      # auth refresh-token store
REDIS_DB_RATELIMIT = 2   # rate-limit counters
REDIS_DB_REALTIME = 3    # WebSocket pub/sub fan-out
REDIS_DB_EVENTS = 4      # event bus streams + consumer groups
REDIS_DB_CACHE = 5       # short-TTL app-data cache (edubridge_shared.cache)


class DepartmentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "department"
    #: PostgreSQL schema owned by this department.
    db_schema: str = "public"

    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # JWT — RS256: only identity holds the private key (its own Settings
    # subclass adds `jwt_private_key`) and can mint tokens; every department
    # (including identity itself, for verification) gets only this public
    # key, which can check a signature but not forge one. Contains the blast
    # radius of a future compromise in any one department to that department
    # alone — under the previous shared-symmetric-secret (HS256) design,
    # compromising *any* department leaked the same secret needed to forge
    # tokens for every other one, including super_admin.
    jwt_public_key: str = Field(default="", alias="JWT_PUBLIC_KEY")
    jwt_algorithm: str = Field(default="RS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=30, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    @field_validator("jwt_public_key", mode="after")
    @classmethod
    def _validate_jwt_public_key(cls, v: str) -> str:
        return _normalize_pem(v)

    # PostgreSQL — one database for the whole platform.
    postgres_user: str = Field(default="edubridge", alias="POSTGRES_USER")
    postgres_password: str = Field(default="edubridge", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="edubridge", alias="POSTGRES_DB")

    # Small pools on purpose: 7 departments x (5 + 2) connections still fits
    # comfortably under Postgres' default max_connections=100.
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=2, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=REDIS_DB_TOKENS, alias="REDIS_DB")

    # The other logical Redis DBs are independently overridable too — not for
    # production (they're deliberately fixed there so every department agrees
    # on where the shared event bus / realtime channel / rate-limit counters
    # live), but so a test suite can point each one at an isolated DB without
    # its events leaking into whatever a developer's `docker compose up` is
    # also using. A prior version hardcoded these, and the test suite's real
    # event publishes ended up in the same event-bus DB a live dev stack reads
    # from, leaving stale unacked messages behind after the tests exited.
    ratelimit_redis_db: int = Field(default=REDIS_DB_RATELIMIT, alias="RATE_LIMIT_REDIS_DB")
    realtime_redis_db: int = Field(default=REDIS_DB_REALTIME, alias="REALTIME_REDIS_DB")
    events_redis_db: int = Field(default=REDIS_DB_EVENTS, alias="EVENTS_REDIS_DB")
    cache_redis_db: int = Field(default=REDIS_DB_CACHE, alias="CACHE_REDIS_DB")

    # Shared secret guarding service-to-service endpoints. When empty the
    # internal guard is disabled (dev convenience only) and a warning is logged.
    internal_secret: str = Field(default="", alias="INTERNAL_SECRET")

    # Event bus (Redis Streams). Entries beyond the cap are trimmed so the bus
    # can never grow without bound on a small host.
    event_stream_maxlen: int = Field(default=10_000, alias="EVENT_STREAM_MAXLEN")

    def _redis_url(self, db: int) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{db}"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL, used by Alembic."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return self._redis_url(self.redis_db)

    @property
    def events_redis_url(self) -> str:
        return self._redis_url(self.events_redis_db)

    @property
    def realtime_redis_url(self) -> str:
        return self._redis_url(self.realtime_redis_db)

    @property
    def ratelimit_redis_url(self) -> str:
        return self._redis_url(self.ratelimit_redis_db)

    @property
    def cache_redis_url(self) -> str:
        return self._redis_url(self.cache_redis_db)

    # A misconfigured .env that's simply missing a variable in production
    # used to fail *open*: an empty INTERNAL_SECRET silently disables the
    # inter-department guard (clients.py's require_internal), and the
    # postgres_password default below is a guessable, publicly-known value.
    # Fail loudly at startup instead of serving traffic with either.
    @model_validator(mode="after")
    def _require_real_secrets_in_production(self) -> "DepartmentSettings":
        if self.environment == "production":
            problems = []
            if not self.internal_secret:
                problems.append("INTERNAL_SECRET is unset (disables inter-department auth)")
            if not self.jwt_public_key:
                problems.append("JWT_PUBLIC_KEY is unset (no department can verify tokens)")
            if self.postgres_password == "edubridge":
                problems.append("POSTGRES_PASSWORD is still the insecure default")
            if problems:
                raise ValueError(
                    "ENVIRONMENT=production but: " + "; ".join(problems)
                )
        return self
