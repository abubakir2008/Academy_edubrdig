"""Lesson lifecycle, notes and homework."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class LessonStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HomeworkStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    SUBMITTED = "submitted"
    GRADED = "graded"


class Lesson(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lessons"

    booking_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    student_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)

    subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=LessonStatus.SCHEDULED.value, nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    recording_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    tutor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    student_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    homeworks: Mapped[list["Homework"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", lazy="selectin"
    )


class Homework(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "homeworks"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=HomeworkStatus.ASSIGNED.value, nullable=False
    )
    submission_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    lesson: Mapped["Lesson"] = relationship(back_populates="homeworks")
