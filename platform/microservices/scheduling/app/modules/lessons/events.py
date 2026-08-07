"""Event wiring for the Lesson Service (producer + consumer).

Consumes ``booking.confirmed`` and autonomously creates the lesson, so a
confirmed booking becomes a schedulable lesson with no extra client call.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from edubridge_shared.events import Topics

from ...events import bus
from ..booking.models.booking import Booking
from .crud import lesson as crud
from .db.session import SessionLocal


async def _on_booking_confirmed(data: dict, topic: str) -> None:
    booking_id = uuid.UUID(data["booking_id"])
    async with SessionLocal() as db:
        # Idempotent: a redelivered event must not create a duplicate lesson.
        existing = await crud.get_by_booking(db, booking_id)
        if existing is not None:
            return
        lesson = await crud.create(
            db,
            {
                "booking_id": booking_id,
                "student_id": uuid.UUID(data["student_id"]),
                "tutor_id": uuid.UUID(data["tutor_id"]),
                "scheduled_start": datetime.fromisoformat(data["scheduled_start"]),
                "duration_minutes": int(data.get("duration_minutes", 60)),
            },
        )
        # Booking and Lessons share one department engine (see db/session.py),
        # so this is an in-process write, not a network call — same pattern
        # Booking already uses to consult Calendar. Without this, a confirmed
        # booking's `lesson_id` stayed null forever: the "join call" button
        # and the new lesson screen both key off that field.
        booking = await db.get(Booking, booking_id)
        if booking is not None:
            booking.lesson_id = lesson.id
            await db.commit()


bus.on(Topics.BOOKING_CONFIRMED, _on_booking_confirmed)
