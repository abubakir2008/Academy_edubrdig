"""Database access for user profiles."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth.models.user import User
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


async def get_tutor(db: AsyncSession, user_id: uuid.UUID) -> Profile | None:
    """Same role/active filter as list_tutors, for the single-tutor detail
    page — a non-tutor id 404s here instead of leaking whatever happens to
    be in their profile row."""
    stmt = (
        select(Profile)
        .join(User, User.id == Profile.user_id)
        .where(Profile.user_id == user_id, User.role == "tutor", User.is_active.is_(True))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_tutors(db: AsyncSession, category_id: uuid.UUID | None = None) -> list[Profile]:
    """Every active tutor's profile — joined against `auth.users` here (not
    exposed as a separate call) purely to filter by role; nothing from User
    itself is selected, so a tutor with no Profile row yet just doesn't show
    up on the public page instead of erroring (they haven't filled anything
    in to display yet anyway)."""
    stmt = (
        select(Profile)
        .join(User, User.id == Profile.user_id)
        .where(User.role == "tutor", User.is_active.is_(True))
    )
    if category_id is not None:
        stmt = stmt.where(Profile.category_ids.any(category_id))
    result = await db.execute(stmt.order_by(Profile.full_name))
    return list(result.scalars().all())
