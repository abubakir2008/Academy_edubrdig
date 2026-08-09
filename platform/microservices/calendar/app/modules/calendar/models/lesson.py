"""Lesson (calendar event) model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class LessonStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


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

    # Zoom conference for this specific lesson instance (one per lesson, not
    # one per series — see services/zoom_client.py). Null only if the lesson
    # predates the Zoom integration; a fresh POST /calendar/lessons always
    # fills these in or fails outright (see the route's hard-fail policy).
    zoom_meeting_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    #: Host-start link — only ever returned by the API to the lesson's own
    #: teacher or staff, never to a student (see LessonOut construction).
    start_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
