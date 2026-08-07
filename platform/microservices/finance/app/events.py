"""Event bus for the Finance department.

Payments publishes ``payment.succeeded``/``payment.refunded``; Wallet consumes
``payment.succeeded`` to credit the tutor's balance (idempotently — see
``modules/wallet/crud/wallet.py::credit_exists``).
"""

from __future__ import annotations

from edubridge_shared.events import EventBus

from .core.config import get_settings

_settings = get_settings()

bus = EventBus(
    redis_url=_settings.events_redis_url,
    service_name=_settings.service_name,
    maxlen=_settings.event_stream_maxlen,
)
