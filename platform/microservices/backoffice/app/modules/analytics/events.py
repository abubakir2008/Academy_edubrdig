"""Event wiring for the Analytics Service (consumer).

Records every platform event into the event log so the metrics endpoints have
data to aggregate — no manual ingestion needed.
"""

from __future__ import annotations

import uuid

from edubridge_shared.events import Topics

from ...events import bus
from .db.session import SessionLocal
from .models.event import EventLog

_ALL_TOPICS = [
    Topics.USER_REGISTERED,
]


def _pick_user(data: dict) -> uuid.UUID | None:
    for key in ("user_id", "student_id", "author_id", "tutor_id"):
        value = data.get(key)
        if value:
            try:
                return uuid.UUID(value)
            except (ValueError, TypeError):
                return None
    return None


async def _record(data: dict, topic: str) -> None:
    async with SessionLocal() as db:
        db.add(
            EventLog(
                event_type=topic,
                user_id=_pick_user(data),
                value_cents=data.get("amount_cents"),
                payload=data,
            )
        )
        await db.commit()


for _topic in _ALL_TOPICS:
    bus.on(_topic, _record)
