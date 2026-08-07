"""Event bus for the Scheduling department.

Booking publishes; Lessons consumes ``booking.confirmed`` to auto-create the
lesson. Both live in this one bus/consumer-group now.
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
