"""Student-specific data: goals, favorites, learning progress, intake leads."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)

    learning_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_languages: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)), nullable=False, default=list, server_default="{}"
    )
    level: Mapped[str | None] = mapped_column(String(32), nullable=True)  # beginner..advanced

    favorites: Mapped[list["FavoriteTutor"]] = relationship(
        back_populates="student", cascade="all, delete-orphan", lazy="selectin"
    )
    progress: Mapped[list["LearningProgress"]] = relationship(
        back_populates="student", cascade="all, delete-orphan", lazy="selectin"
    )


class FavoriteTutor(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "favorite_tutors"
    __table_args__ = (UniqueConstraint("student_id", "tutor_id", name="uq_student_tutor"),)

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)

    student: Mapped["Student"] = relationship(back_populates="favorites")


class LearningProgress(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "learning_progress"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(64), nullable=False)
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hours_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    student: Mapped["Student"] = relationship(back_populates="progress")


class StudentLead(Base, UUIDMixin, TimestampMixin):
    """A submitted intake form — not tied to an account: the form collects a
    name and contact so staff can follow up even with anonymous visitors."""

    __tablename__ = "student_leads"

    subject: Mapped[str | None] = mapped_column(String(64), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    study_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    destination_country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
