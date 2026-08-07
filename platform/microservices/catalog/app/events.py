"""Event bus for the Catalog department.

Tutors publishes ``tutor.updated`` and consumes ``review.created`` /
``tutor.verified`` to keep its denormalised rating in sync. Search consumes
``tutor.updated`` to keep the Postgres full-text index in sync — all inside
this one department now, so that hop no longer even leaves the process.
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
