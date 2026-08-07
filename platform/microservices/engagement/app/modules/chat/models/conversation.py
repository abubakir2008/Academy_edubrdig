"""Chat models — moved off MongoDB onto the shared Postgres database.

The document shapes are unchanged (a conversation has two participants and a
denormalised last-message preview; a message belongs to one conversation), so
the API contract the frontend already talks to didn't need to change — only
the storage engine did, to fit a 4 GB host without its own Mongo container.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class Conversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        # A conversation is looked up by "do these two already have one?" —
        # sorted so (a, b) and (b, a) hit the same index entry.
        Index("ix_conversations_participants", "participants", postgresql_using="gin"),
    )

    participants: Mapped[list[str]] = mapped_column(ARRAY(String(64)), nullable=False)
    last_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Message(Base, UUIDMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        # Unqualified on purpose: it resolves within this Base's own default
        # schema (set once, dynamically, in db/base.py) rather than pinning
        # the literal "engagement" — the same convention every other
        # module's models use, and what makes a per-test schema work.
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Set when the message carries a file — uploaded straight to MinIO via
    # Content's presigned-upload flow first; chat only ever stores the
    # resulting object reference, never the bytes.
    attachment_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    read_by: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)), nullable=False, default=list, server_default="{}"
    )
