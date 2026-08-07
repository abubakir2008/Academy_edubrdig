"""Scheduling department entrypoint: booking + calendar + lessons + video.

Booking publishes ``booking.confirmed``; Lessons, in the very same process,
consumes it and auto-creates the lesson — that hop used to cross two
containers and a Kafka broker, now it is one asyncio task.
"""

from __future__ import annotations

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .events import bus
from .modules.booking.api.routes import bookings as booking_routes
from .modules.calendar.api.routes import calendar as calendar_routes
from .modules.lessons import events as lessons_events  # noqa: F401 — registers handlers
from .modules.lessons.api.routes import lessons as lessons_routes
from .modules.video.api.routes import video as video_routes

settings = get_settings()

app = create_app(
    title="EduBridge Scheduling Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/booking", "/calendar", "/lessons", "/video"],
    routers=[
        booking_routes.router,
        calendar_routes.router,
        lessons_routes.router,
        video_routes.router,
    ],
    log_level=settings.log_level,
    on_startup=[bus.start_producer, bus.start_consuming],
    on_shutdown=[bus.stop],
)
