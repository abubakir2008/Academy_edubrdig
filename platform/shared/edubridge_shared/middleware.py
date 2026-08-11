"""Common HTTP middleware: CORS and a Redis fixed-window rate limiter.

Applied uniformly to every service (via ``app_factory.create_app`` or by calling
``add_common_middleware`` from a service's custom ``main.py``).
"""

from __future__ import annotations

import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def add_cors(app: FastAPI) -> None:
    # Comma-separated origins, or "*" for dev. Tokens travel in the
    # Authorization header (not cookies), so wildcard origin is safe here.
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window limiter keyed by client IP. Fails open if Redis is down.

    If ``path_prefixes`` is given, only requests whose path starts with one
    of them are limited — everything else passes straight through untouched.
    That lets a department stack a second, much stricter instance of this
    middleware on top of the general one for a specific brute-force-prone
    route (e.g. ``/auth/login``) without tightening the budget for every
    other endpoint it serves.
    """

    def __init__(
        self,
        app,
        redis_url: str,
        limit: int,
        window_seconds: int,
        path_prefixes: tuple[str, ...] | None = None,
        key_prefix: str = "ratelimit",
    ) -> None:
        super().__init__(app)
        self._limit = limit
        self._window = window_seconds
        self._redis = None
        self._redis_url = redis_url
        self._path_prefixes = path_prefixes
        self._key_prefix = key_prefix

    async def _client(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def dispatch(self, request: Request, call_next):
        # Never rate-limit health checks.
        if request.url.path.endswith("/health"):
            return await call_next(request)
        if self._path_prefixes is not None and not any(
            request.url.path.startswith(p) for p in self._path_prefixes
        ):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        window = int(time.time()) // self._window
        key = f"{self._key_prefix}:{ip}:{request.url.path}:{window}"
        try:
            redis = await self._client()
            # One round trip instead of two: INCR then a conditional EXPIRE
            # only needs to happen once per window, but a pipeline still
            # sends both commands together every time — still half the
            # latency of two sequential awaits, on the platform's single
            # busiest piece of middleware (every request, every department).
            async with redis.pipeline(transaction=False) as pipe:
                pipe.incr(key)
                pipe.expire(key, self._window, nx=True)
                count, _ = await pipe.execute()
            if count > self._limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests, slow down."},
                    headers={"Retry-After": str(self._window)},
                )
        except Exception:
            # Redis unavailable → don't block traffic.
            pass
        return await call_next(request)


def add_rate_limit(app: FastAPI, redis_url: str, limit: int, window_seconds: int) -> None:
    app.add_middleware(
        RedisRateLimitMiddleware,
        redis_url=redis_url,
        limit=limit,
        window_seconds=window_seconds,
    )


def add_strict_rate_limit(
    app: FastAPI,
    redis_url: str,
    limit: int,
    window_seconds: int,
    path_prefixes: list[str],
) -> None:
    """A second, stricter rate limiter scoped to specific paths — for a
    single brute-force-prone route (e.g. login) that needs a much lower
    budget than the rest of that department's API. Uses its own Redis key
    prefix so it counts independently of the general limiter."""
    app.add_middleware(
        RedisRateLimitMiddleware,
        redis_url=redis_url,
        limit=limit,
        window_seconds=window_seconds,
        path_prefixes=tuple(path_prefixes),
        key_prefix="ratelimit_strict",
    )


def _redis_url_from_env(explicit: str | None) -> str:
    if explicit:
        return explicit
    host = os.getenv("REDIS_HOST", "redis")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("RATE_LIMIT_REDIS_DB", "2")
    return f"redis://{host}:{port}/{db}"


def add_common_middleware(app: FastAPI, *, redis_url: str | None = None) -> None:
    """CORS everywhere; rate limiting when RATE_LIMIT_PER_MIN > 0 (Redis-backed)."""
    add_cors(app)
    per_min = int(os.getenv("RATE_LIMIT_PER_MIN", "0"))
    if per_min > 0:
        add_rate_limit(app, _redis_url_from_env(redis_url), limit=per_min, window_seconds=60)
