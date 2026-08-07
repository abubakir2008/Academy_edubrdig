"""Review & complaint models."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class ComplaintStatus(str, enum.Enum):
    OPEN = "open"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Review(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "reviews"
    # One review per student per lesson. lesson_id is NOT NULL specifically so
    # this constraint actually fires — Postgres treats every NULL as distinct
    # from every other NULL, so a nullable lesson_id let one account leave
    # unlimited reviews for the same tutor as long as it never sent a
    # lesson_id. Requiring (and verifying, see the route) a real completed
    # lesson closes that off entirely.
    __table_args__ = (
        UniqueConstraint("author_id", "lesson_id", name="uq_author_lesson"),
    )

    author_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    lesson_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)

    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_hidden: Mapped[bool] = mapped_column(default=False, nullable=False)


class Complaint(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "complaints"

    author_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)  # tutor | review
    target_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=ComplaintStatus.OPEN.value, nullable=False, index=True
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
