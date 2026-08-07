"""Event bus for the Backoffice department.

Moderation publishes ``tutor.verified``; Analytics consumes almost every
platform event into its append-only event log for reporting.
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
