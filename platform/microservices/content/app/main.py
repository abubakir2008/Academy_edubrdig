"""Content department entrypoint: cms + localization + ai + storage."""

from __future__ import annotations

import asyncio
import logging

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .modules.ai.api.routes import ai as ai_routes
from .modules.cms.api.routes import content as cms_routes
from .modules.localization.api.routes import localization as localization_routes
from .modules.storage.api.routes import storage as storage_routes
from .modules.storage.storage import ensure_buckets

settings = get_settings()
log = logging.getLogger(settings.service_name)


async def _ensure_buckets() -> None:
    # Best-effort: MinIO is an optional, profile-gated dependency (`profiles:
    # ["full"]` in docker-compose.yml) — cms/localization/ai don't need it at
    # all, so a MinIO that isn't running must not take the whole department
    # down. It used to: an unhandled connection error here raised out of the
    # FastAPI lifespan and uvicorn refused to start at all, even though only
    # the /storage prefix was actually affected.
    try:
        # The MinIO client is synchronous; keep it off the event loop.
        await asyncio.to_thread(ensure_buckets)
    except Exception as exc:
        log.warning("Could not reach MinIO to ensure buckets — /storage will fail until it's up: %s", exc)


app = create_app(
    title="EduBridge Content Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/cms", "/localization", "/ai", "/storage"],
    routers=[cms_routes.router, localization_routes.router, ai_routes.router, storage_routes.router],
    log_level=settings.log_level,
    on_startup=[_ensure_buckets],
)
