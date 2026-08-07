"""CMS content: blog posts, FAQ, pages, policies — unified as Article."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class ContentType(str, enum.Enum):
    BLOG = "blog"
    FAQ = "faq"
    PAGE = "page"
    POLICY = "policy"
    LANDING = "landing"


class Article(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "articles"

    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(16), default=ContentType.BLOG.value, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    seo_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
