"""Booking model — a student reserving a lesson slot with a tutor."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"       # created, awaiting tutor confirmation / payment
    CONFIRMED = "confirmed"   # confirmed, lesson scheduled
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Booking(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "bookings"

    student_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)

    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=BookingStatus.PENDING.value, nullable=False, index=True
    )

    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    payment_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    # Set when this lesson was drawn from a prepaid LessonPackage (Finance) —
    # the frontend uses this to skip showing a "Pay" button entirely.
    package_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
