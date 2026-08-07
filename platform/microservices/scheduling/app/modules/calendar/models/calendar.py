"""Calendar models: weekly availability rules + one-off blocked times."""

from __future__ import annotations

import uuid
from datetime import datetime, time

from sqlalchemy import DateTime, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class AvailabilityRule(Base, UUIDMixin, TimestampMixin):
    """Recurring weekly availability window for a tutor."""

    __tablename__ = "availability_rules"

    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon .. 6=Sun
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)


class BlockedTime(Base, UUIDMixin, TimestampMixin):
    """A specific interval the tutor is unavailable (vacation, personal, etc.)."""

    __tablename__ = "blocked_times"

    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
