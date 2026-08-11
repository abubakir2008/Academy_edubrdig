"""Database access for user profiles."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.profile import Profile


async def get(db: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    return await db.get(Profile, user_id)


async def get_or_create(db: AsyncSession, user_id: uuid.UUID) -> Profile:
    profile = await db.get(Profile, user_id)
    if profile is None:
        profile = Profile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def update(db: AsyncSession, profile: Profile, data: dict) -> Profile:
    for field, value in data.items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_many(db: AsyncSession, user_ids: list[uuid.UUID]) -> list[Profile]:
    result = await db.execute(select(Profile).where(Profile.user_id.in_(user_ids)))
    return list(result.scalars().all())


async def list_profiles(db: AsyncSession, limit: int = 50, offset: int = 0) -> list[Profile]:
    result = await db.execute(
        select(Profile).order_by(Profile.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())
