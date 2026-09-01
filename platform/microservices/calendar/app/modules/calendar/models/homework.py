"""Homework assigned (and graded) coming out of a lesson.

One row per (lesson, student) pair — even a whole-group lesson is graded and
assigned per student, matching how the teacher actually works through a
roster one student at a time. `grade`/`comment` can be set immediately at
creation (grading what just happened in the call) and/or later via the
dedicated grade endpoint (once the student's written submission is in) —
`status` is derived from what's actually been set, not written by the
caller, so it can never drift from the row's real state.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class HomeworkStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    SUBMITTED = "submitted"
    GRADED = "graded"


class Homework(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "homework"

    # Real FK, unlike course_id/teacher_id/student_id below — lessons lives
    # in this same schema (see lesson.py's own note on the cross-schema
    # convention this follows).
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalized from the lesson at creation time (same reasoning as
    # Lesson.teacher_id) so "my homework" queries never need a join.
    course_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=HomeworkStatus.ASSIGNED.value, nullable=False, index=True
    )

    # Student's submitted work — object_name/url from content's storage
    # module (the same direct-upload/relay path avatars use, not a
    # presigned MinIO link; see content/storage.py for why).
    submission_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submission_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
