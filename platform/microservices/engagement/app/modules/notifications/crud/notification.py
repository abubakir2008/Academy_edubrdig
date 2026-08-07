"""Notification persistence (Postgres)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.notification import Notification


async def create(db: AsyncSession, data: dict) -> Notification:
    notification = Notification(**data)
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def list_for_user(
    db: AsyncSession, user_id: str, *, only_unread: bool, limit: int
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if only_unread:
        stmt = stmt.where(Notification.read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def unread_count(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read.is_(False)
        )
    )
    return int(result.scalar_one())


async def mark_read(db: AsyncSession, notification_id: uuid.UUID, user_id: str) -> bool:
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        return False
    notification.read = True
    await db.commit()
    return True


async def mark_all_read(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id, Notification.read.is_(False)
        )
    )
    rows = list(result.scalars().all())
    for row in rows:
        row.read = True
    await db.commit()
    return len(rows)
