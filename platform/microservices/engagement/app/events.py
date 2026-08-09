"""Event bus for the Engagement department.

Notifications consumes platform events to turn them into user-facing
notifications — see ``modules/notifications/events.py`` for the handler
wiring.
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
