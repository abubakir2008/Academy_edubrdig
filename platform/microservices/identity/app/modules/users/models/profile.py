"""Canonical user profile, keyed by the auth user id."""

from __future__ import annotations

import uuid

from sqlalchemy import String
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
