"""Engagement department entrypoint: chat + notifications + support.

All three used to run on their own MongoDB container; they now share one
Postgres schema (``engagement``) and one Redis-backed realtime bus.
"""

from __future__ import annotations

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .events import bus
from .modules.chat.api.routes import chat as chat_routes
from .modules.notifications.api.routes import notifications as notifications_routes
from .modules.support.api.routes import support as support_routes

settings = get_settings()

app = create_app(
    title="EduBridge Engagement Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/chat", "/notifications", "/support"],
    routers=[
        chat_routes.router,
        notifications_routes.router,
        support_routes.router,
    ],
    log_level=settings.log_level,
    on_startup=[bus.start_producer, bus.start_consuming],
    on_shutdown=[bus.stop],
)
