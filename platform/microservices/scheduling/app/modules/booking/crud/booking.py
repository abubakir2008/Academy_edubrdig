"""Booking persistence + overlap checks."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.booking import Booking, BookingStatus

_ACTIVE = (BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value)


async def has_overlap(
    db: AsyncSession,
    tutor_id: uuid.UUID,
    start: datetime,
    end: datetime,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    """True if the tutor already has an active booking overlapping [start, end)."""
    stmt = select(Booking.id).where(
        Booking.tutor_id == tutor_id,
        Booking.status.in_(_ACTIVE),
        # overlap: existing.start < new.end AND existing.end > new.start
        and_(Booking.scheduled_start < end, Booking.scheduled_end > start),
    )
    if exclude_id is not None:
        stmt = stmt.where(Booking.id != exclude_id)
    result = await db.execute(stmt.limit(1))
    return result.first() is not None


async def has_used_trial(db: AsyncSession, student_id: uuid.UUID, tutor_id: uuid.UUID) -> bool:
    """True if this student already has a non-cancelled trial booking with this tutor.

    One trial per student/tutor pair, same rule Preply enforces — otherwise a
    student could take the discounted-or-free trial slot from the same tutor
    indefinitely.
    """
    stmt = (
        select(Booking.id)
        .where(
            Booking.student_id == student_id,
            Booking.tutor_id == tutor_id,
            Booking.is_trial.is_(True),
            Booking.status != BookingStatus.CANCELLED.value,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.first() is not None


async def create(db: AsyncSession, student_id: uuid.UUID, data: dict) -> Booking:
    start: datetime = data["scheduled_start"]
    end = start + timedelta(minutes=data["duration_minutes"])
    booking = Booking(
        student_id=student_id,
        tutor_id=data["tutor_id"],
        scheduled_start=start,
        scheduled_end=end,
        duration_minutes=data["duration_minutes"],
        is_trial=data.get("is_trial", False),
        price_cents=data.get("price_cents", 0),
        currency=data.get("currency", "USD"),
        package_id=data.get("package_id"),
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


async def get(db: AsyncSession, booking_id: uuid.UUID) -> Booking | None:
    return await db.get(Booking, booking_id)


async def list_for_user(
    db: AsyncSession, user_id: uuid.UUID, as_role: str, status: str | None
) -> list[Booking]:
    col = Booking.tutor_id if as_role == "tutor" else Booking.student_id
    stmt = select(Booking).where(col == user_id)
    if status:
        stmt = stmt.where(Booking.status == status)
    stmt = stmt.order_by(Booking.scheduled_start.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def save(db: AsyncSession, booking: Booking) -> Booking:
    await db.commit()
    await db.refresh(booking)
    return booking
