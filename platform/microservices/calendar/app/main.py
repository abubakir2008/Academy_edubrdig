"""Calendar department entrypoint: advanced scheduling for courses."""

from __future__ import annotations

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .modules.calendar.api.routes import calendar as calendar_routes

settings = get_settings()

app = create_app(
    title="EduBridge Calendar Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/calendar"],
    routers=[calendar_routes.router],
    log_level=settings.log_level,
)
