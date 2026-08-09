"""ZoomAccount persistence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.zoom_account import ZoomAccount


async def get_for_tutor(db: AsyncSession, tutor_id: uuid.UUID) -> ZoomAccount | None:
    result = await db.execute(select(ZoomAccount).where(ZoomAccount.tutor_id == tutor_id))
    return result.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    tutor_id: uuid.UUID,
    *,
    access_token: str,
    refresh_token: str,
    token_expires_at: datetime,
    zoom_email: str | None,
) -> ZoomAccount:
    account = await get_for_tutor(db, tutor_id)
    if account is None:
        account = ZoomAccount(tutor_id=tutor_id)
        db.add(account)
    account.access_token = access_token
    account.refresh_token = refresh_token
    account.token_expires_at = token_expires_at
    account.zoom_email = zoom_email
    await db.commit()
    await db.refresh(account)
    return account


async def save_tokens(
    db: AsyncSession, account: ZoomAccount, *, access_token: str, refresh_token: str, token_expires_at: datetime
) -> ZoomAccount:
    account.access_token = access_token
    account.refresh_token = refresh_token
    account.token_expires_at = token_expires_at
    await db.commit()
    await db.refresh(account)
    return account


async def delete_for_tutor(db: AsyncSession, tutor_id: uuid.UUID) -> bool:
    result = await db.execute(sa_delete(ZoomAccount).where(ZoomAccount.tutor_id == tutor_id))
    await db.commit()
    return result.rowcount > 0
