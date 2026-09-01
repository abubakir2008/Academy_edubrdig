"""Notification preference persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.preference import NotificationPreference


async def get_or_create(db: AsyncSession, user_id: str) -> NotificationPreference:
    result = await db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    pref = result.scalar_one_or_none()
    if pref is not None:
        return pref
    pref = NotificationPreference(user_id=user_id)
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return pref


async def update(db: AsyncSession, pref: NotificationPreference, data: dict) -> NotificationPreference:
    for field, value in data.items():
        setattr(pref, field, value)
    await db.commit()
    await db.refresh(pref)
    return pref
