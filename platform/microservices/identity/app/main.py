"""Identity department entrypoint: auth (login/register/refresh/OAuth) + users
(profile CRUD). One process, one Postgres schema, one Redis-backed token store.
"""

from __future__ import annotations

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .events import bus
from .modules.auth.api.routes import admin_users as admin_users_routes
from .modules.auth.api.routes import auth as auth_routes
from .modules.auth.api.routes import health as auth_health_routes
from .modules.users.api.routes import profiles as users_routes

settings = get_settings()

app = create_app(
    title="EduBridge Identity Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/auth", "/users"],
    routers=[auth_routes.router, admin_users_routes.router, users_routes.router, auth_health_routes.router],
    log_level=settings.log_level,
    on_startup=[bus.start_producer],
    on_shutdown=[bus.stop],
)
