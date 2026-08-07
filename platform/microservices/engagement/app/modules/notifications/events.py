"""Event wiring for the Notifications module (consumer).

Turns domain events from across the platform into user notifications — the
frontend never has to ask "did anything happen?", the notification just
appears. Handlers are registered on the department-wide bus (see
``app/events.py``); the bus itself now guarantees at-least-once, exactly-once
in the common case, delivery (see ``edubridge_shared.events``), so a handler
only needs to be safe against processing the *same* event twice, not against
losing it.
"""

from __future__ import annotations

from edubridge_shared.events import Topics

from ...events import bus
from .crud import notification as crud
from .db.session import SessionLocal
from .realtime import bus as rt_bus
from .realtime import user_channel


async def _notify(user_id: str | None, ntype: str, title: str, body: str, channel: str = "push") -> None:
    if not user_id:
        return
    async with SessionLocal() as db:
        notification = await crud.create(
            db,
            {
                "user_id": user_id,
                "type": ntype,
                "title": title,
                "body": body,
                "channel": channel,
            },
        )
    await rt_bus.publish(
        user_channel(user_id),
        {"id": str(notification.id), "type": ntype, "title": title, "body": body},
    )


async def _on_payment(data: dict, topic: str) -> None:
    await _notify(data.get("student_id"), "payment", "Payment successful",
                  "Your payment was received.")
    await _notify(data.get("tutor_id"), "earnings", "New earnings",
                  "You received earnings from a lesson purchase.")


async def _on_booking_created(data: dict, topic: str) -> None:
    await _notify(data.get("tutor_id"), "booking", "New booking request",
                  "A student booked a lesson with you.")


async def _on_booking_confirmed(data: dict, topic: str) -> None:
    await _notify(data.get("student_id"), "booking", "Booking confirmed",
                  "Your lesson booking has been confirmed.")


async def _on_booking_cancelled(data: dict, topic: str) -> None:
    canceller = data.get("cancelled_by")
    for uid in (data.get("student_id"), data.get("tutor_id")):
        if uid and uid != canceller:
            await _notify(uid, "booking", "Booking cancelled", "A booking was cancelled.")


async def _on_lesson_completed(data: dict, topic: str) -> None:
    await _notify(data.get("student_id"), "review", "How was your lesson?",
                  "Leave a review for your tutor.")


async def _on_review_created(data: dict, topic: str) -> None:
    await _notify(data.get("tutor_id"), "review", "New review",
                  "You received a new review.")


async def _on_tutor_verified(data: dict, topic: str) -> None:
    await _notify(data.get("tutor_id"), "verification", "Profile verified",
                  "Congratulations — your tutor profile is now verified.")


bus.on(Topics.PAYMENT_SUCCEEDED, _on_payment)
bus.on(Topics.BOOKING_CREATED, _on_booking_created)
bus.on(Topics.BOOKING_CONFIRMED, _on_booking_confirmed)
bus.on(Topics.BOOKING_CANCELLED, _on_booking_cancelled)
bus.on(Topics.LESSON_COMPLETED, _on_lesson_completed)
bus.on(Topics.REVIEW_CREATED, _on_review_created)
bus.on(Topics.TUTOR_VERIFIED, _on_tutor_verified)
