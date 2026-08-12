"""Canonical user profile, keyed by the auth user id."""

from __future__ import annotations

import uuid

from sqlalchemy import ARRAY, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin

from ..db.base import Base


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    # Primary key IS the auth service user id (shared identity, no cross-db FK).
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)

    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Public tutor-profile fields — only meaningful for role="tutor" accounts
    # (nothing enforces that at the DB level; the /users/tutors routes are
    # what actually filters by role), populated by the tutor themselves via
    # PUT /users/me, same as full_name/avatar_url above.
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: One-liner shown on the public tutor card (matches "Системный подход,
    #: легко адаптируется..." in the reference design).
    bio_short: Mapped[str | None] = mapped_column(String(280), nullable=True)
    #: Longer write-up, shown only on the tutor's own full profile page.
    bio_full: Mapped[str | None] = mapped_column(Text, nullable=True)
    languages: Mapped[list[str] | None] = mapped_column(ARRAY(String(64)), nullable=True)
    #: References academics' Category.id — cross-department, so a plain
    #: array of ids rather than a real FK (same convention as calendar's
    #: course_id/teacher_id).
    category_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(PgUUID(as_uuid=True)), nullable=True)
