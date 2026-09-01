"""Expo push tokens — one row per device a user has ever logged into.

`token` is the unique key (not `(user_id, token)`): a physical device only
ever has one Expo push token, so if a token shows up again under a different
user it means someone logged out and a different account logged in on that
same device — re-registering should move it, not create a second live row
still pointing push notifications at the previous account.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class PushToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "push_tokens"

    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
