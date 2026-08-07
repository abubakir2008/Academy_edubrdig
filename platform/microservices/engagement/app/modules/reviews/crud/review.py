"""Review & complaint persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.review import Complaint, Review


async def create_review(db: AsyncSession, author_id: uuid.UUID, data: dict) -> Review:
    review = Review(author_id=author_id, **data)
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def get_review(db: AsyncSession, review_id: uuid.UUID) -> Review | None:
    return await db.get(Review, review_id)


async def list_for_tutor(db: AsyncSession, tutor_id: uuid.UUID, limit: int, offset: int) -> list[Review]:
    result = await db.execute(
        select(Review)
        .where(Review.tutor_id == tutor_id, Review.is_hidden.is_(False))
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def tutor_summary(db: AsyncSession, tutor_id: uuid.UUID) -> tuple[float, int]:
    result = await db.execute(
        select(func.coalesce(func.avg(Review.rating), 0), func.count(Review.id)).where(
            Review.tutor_id == tutor_id, Review.is_hidden.is_(False)
        )
    )
    avg, count = result.one()
    return round(float(avg), 2), int(count)


async def delete_review(db: AsyncSession, review: Review) -> None:
    await db.delete(review)
    await db.commit()


async def create_complaint(db: AsyncSession, author_id: uuid.UUID, data: dict) -> Complaint:
    complaint = Complaint(author_id=author_id, **data)
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)
    return complaint


async def get_complaint(db: AsyncSession, cid: uuid.UUID) -> Complaint | None:
    return await db.get(Complaint, cid)


async def list_complaints(db: AsyncSession, status: str | None) -> list[Complaint]:
    stmt = select(Complaint).order_by(Complaint.created_at.desc())
    if status:
        stmt = stmt.where(Complaint.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def save(db: AsyncSession, obj):
    await db.commit()
    await db.refresh(obj)
    return obj
