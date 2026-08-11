"""Identity department entrypoint: auth (login/register/refresh/OAuth) + users
(profile CRUD). One process, one Postgres schema, one Redis-backed token store.
"""

from __future__ import annotations

from edubridge_shared.app_factory import create_app
from edubridge_shared.middleware import add_strict_rate_limit

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

# Login is the platform's single most valuable brute-force target — a
# dedicated, much stricter limiter on top of the general one (which every
# department gets from create_app), so it can't be loosened by whatever the
# general RATE_LIMIT_PER_MIN is tuned to for normal traffic.
if settings.auth_rate_limit_per_min > 0:
    add_strict_rate_limit(
        app,
        redis_url=settings.ratelimit_redis_url,
        limit=settings.auth_rate_limit_per_min,
        window_seconds=60,
        path_prefixes=["/auth/login"],
    )
