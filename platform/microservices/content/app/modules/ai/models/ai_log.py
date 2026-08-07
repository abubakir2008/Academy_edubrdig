"""Log of AI feature invocations (powers the admin "AI Logs" view)."""

from __future__ import annotations

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class AiRequestLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "ai_request_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
