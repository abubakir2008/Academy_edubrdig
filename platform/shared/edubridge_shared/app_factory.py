"""Factory that builds a consistent FastAPI app for a department.

Wires structured logging, the given routers and a ``/<prefix>/health`` endpoint
for **every** route prefix the department serves — so a department that took
over ``/booking``, ``/calendar``, ``/lessons`` and ``/video`` still answers
``/booking/health`` exactly as the standalone service used to. That keeps the
gateway config, the frontend and any external health check unchanged.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Sequence
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from .logging import configure_logging
from .middleware import add_common_middleware
from .schemas import HealthResponse

Hook = Callable[[], Awaitable[None]]


def create_app(
    *,
    title: str,
    service_name: str,
    version: str,
    route_prefixes: Sequence[str],
    routers: Iterable[APIRouter],
    log_level: str = "INFO",
    on_startup: Iterable[Hook] | None = None,
    on_shutdown: Iterable[Hook] | None = None,
    redis_url: str | None = None,
) -> FastAPI:
    configure_logging(service_name, log_level)

    _startup = list(on_startup or [])
    _shutdown = list(on_shutdown or [])

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        for hook in _startup:
            await hook()
        yield
        for hook in _shutdown:
            await hook()

    app = FastAPI(title=title, version=version, lifespan=lifespan)
    add_common_middleware(app, redis_url=redis_url)

    for prefix in route_prefixes:
        health = APIRouter(prefix=prefix, tags=["health"])

        # Bind the prefix per iteration; a closure over the loop variable would
        # make every endpoint report the last prefix.
        def _make(module: str = prefix.lstrip("/")):
            async def health_check() -> HealthResponse:
                return HealthResponse(
                    status="ok", service=f"{service_name}:{module}", version=version
                )

            return health_check

        health.add_api_route(
            "/health", _make(), methods=["GET"], response_model=HealthResponse
        )
        app.include_router(health)

    for router in routers:
        app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, object]:
        return {
            "service": service_name,
            "version": version,
            "modules": [p.lstrip("/") for p in route_prefixes],
        }

    return app
