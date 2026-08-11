"""Chat persistence (Postgres)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.conversation import Conversation, Message


async def find_by_participants(db: AsyncSession, participants: list[str]) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.participants == participants)
    )
    return result.scalars().first()


async def create_conversation(db: AsyncSession, participants: list[str]) -> Conversation:
    conv = Conversation(participants=participants)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def list_for_user(db: AsyncSession, user_id: str) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.participants.any(user_id))
        .order_by(Conversation.last_message_at.desc().nulls_last())
    )
    return list(result.scalars().all())


async def get_conversation(db: AsyncSession, cid: uuid.UUID) -> Conversation | None:
    return await db.get(Conversation, cid)


async def add_message(
    db: AsyncSession,
    conversation: Conversation,
    sender_id: str,
    text: str,
    now: datetime,
    attachment_url: str | None = None,
    attachment_name: str | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation.id,
        sender_id=sender_id,
        text=text,
        created_at=now,
        read_by=[sender_id],
        attachment_url=attachment_url,
        attachment_name=attachment_name,
    )
    db.add(message)
    conversation.last_text = text if not attachment_url else f"📎 {attachment_name or text}"
    conversation.last_message_at = now
    await db.commit()
    await db.refresh(message)
    return message


async def list_messages(db: AsyncSession, conversation_id: uuid.UUID, limit: int) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def mark_read(db: AsyncSession, conversation_id: uuid.UUID, user_id: str) -> int:
    result = await db.execute(
        update(Message)
        .where(
            Message.conversation_id == conversation_id,
            ~Message.read_by.any(user_id),
        )
        .values(read_by=func.array_append(Message.read_by, user_id))
    )
    await db.commit()
    return result.rowcount
