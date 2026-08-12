"""Lead persistence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.lead import Lead


async def create(db: AsyncSession, data: dict) -> Lead:
    lead = Lead(**data)
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def find_recent_by_contact(
    db: AsyncSession, *, contact_phone: str | None, contact_email: str | None, since: datetime
) -> Lead | None:
    """Most recent lead sharing this phone or email, created since `since` —
    used to catch double-submits and repeat spam before writing another row.
    Returns None if neither contact field is given (nothing to match on)."""
    conditions = []
    if contact_phone:
        conditions.append(Lead.contact_phone == contact_phone)
    if contact_email:
        conditions.append(Lead.contact_email == contact_email)
    if not conditions:
        return None
    stmt = (
        select(Lead)
        .where(or_(*conditions), Lead.created_at >= since)
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get(db: AsyncSession, lead_id: uuid.UUID) -> Lead | None:
    return await db.get(Lead, lead_id)


async def list_all(db: AsyncSession, status: str | None) -> list[Lead]:
    stmt = select(Lead).order_by(Lead.created_at.desc())
    if status is not None:
        stmt = stmt.where(Lead.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_for_tutor(db: AsyncSession, tutor_id: uuid.UUID, status: str | None) -> list[Lead]:
    """Leads submitted via this specific tutor's public profile ("Оставить
    заявку") — a tutor only ever sees their own, staff see everything via
    list_all above."""
    stmt = select(Lead).where(Lead.preferred_tutor_id == tutor_id).order_by(Lead.created_at.desc())
    if status is not None:
        stmt = stmt.where(Lead.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_status(db: AsyncSession, lead: Lead, status: str) -> Lead:
    lead.status = status
    await db.commit()
    await db.refresh(lead)
    return lead
