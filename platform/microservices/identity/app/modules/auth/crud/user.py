"""Database access for the User model."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def list_all(db: AsyncSession, role: str | None = None) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if role:
        stmt = stmt.where(User.role == role)
    result = await db.execute(stmt)
    return list(result.scalars())


async def update(db: AsyncSession, user: User, data: dict) -> User:
    for field, value in data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.commit()


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    hashed_password: str | None,
    full_name: str | None,
    role: str,
    oauth_provider: str | None = None,
    oauth_subject: str | None = None,
    is_verified: bool = False,
) -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role,
        oauth_provider=oauth_provider,
        oauth_subject=oauth_subject,
        is_verified=is_verified,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
