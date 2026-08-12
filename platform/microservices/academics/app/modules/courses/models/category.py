"""Course/tutor subject category — plain taxonomy, managed by staff."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class Category(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
