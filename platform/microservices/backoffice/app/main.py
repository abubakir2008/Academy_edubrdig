"""Backoffice department entrypoint: admin + moderation + analytics."""

from __future__ import annotations

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .events import bus
from .modules.admin.api.routes import admin as admin_routes
from .modules.analytics import events as analytics_events  # noqa: F401 — registers handlers
from .modules.analytics.api.routes import analytics as analytics_routes
from .modules.moderation.api.routes import moderation as moderation_routes

settings = get_settings()

app = create_app(
    title="EduBridge Backoffice Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/admin", "/moderation", "/analytics"],
    routers=[admin_routes.router, moderation_routes.router, analytics_routes.router],
    log_level=settings.log_level,
    on_startup=[bus.start_producer, bus.start_consuming],
    on_shutdown=[bus.stop],
)
