"""Finance department entrypoint: payments + wallet.

Payments publishes ``payment.succeeded``; Wallet consumes it in-process to
credit the tutor's balance idempotently.
"""

from __future__ import annotations

from edubridge_shared.app_factory import create_app

from . import __version__
from .core.config import get_settings
from .events import bus
from .modules.payments.api.routes import payments as payments_routes
from .modules.wallet import events as wallet_events  # noqa: F401 — registers handlers
from .modules.wallet.api.routes import wallet as wallet_routes

settings = get_settings()

app = create_app(
    title="EduBridge Finance Department",
    service_name=settings.service_name,
    version=__version__,
    route_prefixes=["/payments", "/wallet"],
    routers=[payments_routes.router, wallet_routes.router],
    log_level=settings.log_level,
    on_startup=[bus.start_producer, bus.start_consuming],
    on_shutdown=[bus.stop],
)
