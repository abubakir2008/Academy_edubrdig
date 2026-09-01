"""Per-user push preferences, one row per user, created lazily on first
read/write (see crud/preference.py's get_or_create) — a user who's never
touched their settings gets the same defaults (everything on) as one who
explicitly turned everything on.

Only gates the push channel. The in-app list (GET /notifications/me) and
the live WebSocket push are unaffected — turning off "chat messages" here
just means no push arrives while the app is backgrounded, not that the
message disappears from the thread.
"""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class NotificationPreference(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    lesson_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    chat_messages: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    homework: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
