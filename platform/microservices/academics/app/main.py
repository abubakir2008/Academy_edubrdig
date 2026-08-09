"""Academics department entrypoint: courses."""

from __future__ import annotations

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .modules.courses.api.routes import courses as courses_routes

settings = get_settings()

app = create_app(
    title="EduBridge Academics Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/courses"],
    routers=[courses_routes.router],
    log_level=settings.log_level,
)
