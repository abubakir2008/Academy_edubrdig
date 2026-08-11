"""Notification model — moved off MongoDB onto the shared Postgres database."""

from __future__ import annotations

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"
    # list_for_user/unread_count/mark_all_read all filter on this pair together.
    __table_args__ = (Index("ix_notifications_user_id_read", "user_id", "read"),)

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), default="system", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(String(16), default="push", nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
