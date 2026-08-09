"""A tutor's linked Zoom account (per-tutor OAuth, not one shared account)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class ZoomAccount(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "zoom_accounts"

    # One Zoom connection per tutor.
    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, unique=True, index=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: For "Connected as x@mail.com" in the UI — not used for auth.
    zoom_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
