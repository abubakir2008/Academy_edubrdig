"""Lesson (calendar event) model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class LessonStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    #: Never written to the `status` column — computed on read (see
    #: routes/calendar.py:_lesson_out) whenever a lesson is still
    #: "scheduled" but its scheduled_end is in the past. Documented here
    #: only so every consumer of LessonStatus sees it as a real value.
    MISSED = "missed"


class Lesson(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lessons"

    # Plain columns, not FKs — academics' courses/identity's users live in
    # different schemas (departments never declare cross-schema foreign
    # keys). teacher_id is denormalized from the course at creation time so
    # conflict checks and "my lessons" queries never need a cross-service call.
    course_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    # Groups the instances of a weekly-recurring request together; null for
    # a one-off lesson.
    series_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True, index=True)

    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=LessonStatus.SCHEDULED.value, nullable=False, index=True)

    #: Both optional — null falls back to "Урок" / the course description
    #: wherever they're displayed (see LessonOut construction and the
    #: frontend's NextLessonCard).
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # No video-conference fields here on purpose: the LiveKit room for a
    # lesson isn't stored anywhere — it's derived from the lesson's own id
    # (see services/livekit_client.py::room_name) and a join token is minted
    # fresh on every request, not created/persisted ahead of time the way the
    # old Zoom integration's meeting_id/meeting_url/start_url were.
