"""Database access for the User model."""

from __future__ import annotations

import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def get_by_referral_code(db: AsyncSession, code: str) -> User | None:
    result = await db.execute(select(User).where(User.referral_code == code.upper()))
    return result.scalar_one_or_none()


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


def _new_referral_code() -> str:
    # 8 chars of base32-ish alphabet, no ambiguous 0/O/1/I — friendly to read
    # aloud and to type into a "have a referral code?" field.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


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
    referred_by_id: uuid.UUID | None = None,
) -> User:
    for _ in range(5):  # collision odds are astronomically low; a retry is just cheap insurance
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            oauth_provider=oauth_provider,
            oauth_subject=oauth_subject,
            is_verified=is_verified,
            referral_code=_new_referral_code(),
            referred_by_id=referred_by_id,
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        await db.refresh(user)
        return user
    raise RuntimeError("Could not generate a unique referral code")
