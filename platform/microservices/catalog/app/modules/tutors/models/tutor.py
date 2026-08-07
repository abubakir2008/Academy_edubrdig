"""Tutor profile and related settings."""

from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import Boolean, Computed, ForeignKey, Index, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base

# ElasticSearch used to hold a separate copy of this data purely for full-text
# search. That meant a whole extra container plus a Kafka-driven reindex to
# keep it in sync — too much for a 4 GB host, and a duplicate source of truth.
# Instead this generated column keeps a ranked search vector as part of the
# tutor row itself: Postgres updates it automatically on every write, and the
# GIN index below makes ``@@`` queries on it fast at this table's scale.
_SEARCH_VECTOR_EXPR = (
    "setweight(to_tsvector('simple', coalesce(headline, '')), 'A') || "
    "setweight(to_tsvector('simple', coalesce(description, '')), 'B')"
)


class Tutor(Base, TimestampMixin):
    __tablename__ = "tutors"
    __table_args__ = (
        Index("ix_tutors_search_vector", "search_vector", postgresql_using="gin"),
    )

    # PK is the auth user id (shared identity).
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)

    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    native_language: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Languages the tutor teaches in / categories (subjects) they cover.
    languages_taught: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)), nullable=False, default=list, server_default="{}"
    )
    specializations: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)), nullable=False, default=list, server_default="{}"
    )

    experience_years: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Prices are stored as integer minor units (e.g. cents) to avoid float issues.
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trial_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Denormalised aggregates kept in sync by the Review / Lesson services.
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_lessons: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Auto-maintained by Postgres — never assigned from Python.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR, Computed(_SEARCH_VECTOR_EXPR, persisted=True), nullable=True
    )

    working_hours: Mapped[list["WorkingHour"]] = relationship(
        back_populates="tutor", cascade="all, delete-orphan", lazy="selectin"
    )
    certificates: Mapped[list["Certificate"]] = relationship(
        back_populates="tutor", cascade="all, delete-orphan", lazy="selectin"
    )


class WorkingHour(Base, UUIDMixin):
    """A recurring weekly availability window for a tutor."""

    __tablename__ = "working_hours"

    tutor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tutors.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon .. 6=Sun
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    tutor: Mapped["Tutor"] = relationship(back_populates="working_hours")


class Certificate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "certificates"

    tutor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tutors.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    issued_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    tutor: Mapped["Tutor"] = relationship(back_populates="certificates")
