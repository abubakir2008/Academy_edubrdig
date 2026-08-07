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
    """Fixed-window limiter keyed by client IP. Fails open if Redis is down."""

    def __init__(self, app, redis_url: str, limit: int, window_seconds: int) -> None:
        super().__init__(app)
        self._limit = limit
        self._window = window_seconds
        self._redis = None
        self._redis_url = redis_url

    async def _client(self):
        if self._redis is None:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def dispatch(self, request: Request, call_next):
        # Never rate-limit health checks.
        if request.url.path.endswith("/health"):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        window = int(time.time()) // self._window
        key = f"ratelimit:{ip}:{request.url.path}:{window}"
        try:
            redis = await self._client()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, self._window)
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
