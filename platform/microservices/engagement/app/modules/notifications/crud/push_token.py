"""Push token persistence (Postgres)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.push_token import PushToken


async def register(db: AsyncSession, user_id: str, token: str, platform: str) -> None:
    """Upsert on `token`: a re-registration (app relaunch, or a different
    account logging into the same device) always wins over whatever row was
    there before — see the model's docstring for why `token` alone is unique."""
    stmt = insert(PushToken).values(user_id=user_id, token=token, platform=platform)
    stmt = stmt.on_conflict_do_update(
        index_elements=[PushToken.token],
        set_={"user_id": user_id, "platform": platform},
    )
    await db.execute(stmt)
    await db.commit()


async def unregister(db: AsyncSession, token: str) -> None:
    await db.execute(delete(PushToken).where(PushToken.token == token))
    await db.commit()


async def tokens_for_user(db: AsyncSession, user_id: str) -> list[str]:
    result = await db.execute(select(PushToken.token).where(PushToken.user_id == user_id))
    return list(result.scalars().all())
