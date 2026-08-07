"""Localization: supported languages + translation strings."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class Language(Base, TimestampMixin):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)  # e.g. en, ru, es
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Translation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "translations"
    __table_args__ = (UniqueConstraint("locale", "key", name="uq_locale_key"),)

    locale: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
