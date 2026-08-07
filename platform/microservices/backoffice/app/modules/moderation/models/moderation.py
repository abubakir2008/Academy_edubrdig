"""Moderation: tutor verification requests and document reviews."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class ModStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class VerificationRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "verification_requests"

    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), default="profile", nullable=False)  # profile|identity
    status: Mapped[str] = mapped_column(
        String(16), default=ModStatus.PENDING.value, nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)


class Document(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "documents"

    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)  # diploma|id|certificate
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=ModStatus.PENDING.value, nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
