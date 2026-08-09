"""Course and enrollment models."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class Course(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "courses"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Plain column, not a FK — identity's users live in a different schema
    # (departments never declare cross-schema foreign keys, see engagement's
    # models for the same convention). Exactly one teacher per course.
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True, index=True)


class Enrollment(Base, UUIDMixin, TimestampMixin):
    """A student's membership in a course — the course's roster ("group")."""

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_enrollments_course_student"),)

    course_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        # Unqualified on purpose — resolves within this Base's own schema;
        # see the same note in engagement/support/models/ticket.py.
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
