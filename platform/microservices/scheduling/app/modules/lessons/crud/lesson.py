"""Lesson & homework persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.lesson import Homework, Lesson


async def create(db: AsyncSession, data: dict) -> Lesson:
    lesson = Lesson(**data)
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def get(db: AsyncSession, lesson_id: uuid.UUID) -> Lesson | None:
    return await db.get(Lesson, lesson_id)


async def get_by_booking(db: AsyncSession, booking_id: uuid.UUID) -> Lesson | None:
    result = await db.execute(select(Lesson).where(Lesson.booking_id == booking_id))
    return result.scalar_one_or_none()


async def list_for_user(db: AsyncSession, user_id: uuid.UUID, status: str | None) -> list[Lesson]:
    stmt = select(Lesson).where(
        or_(Lesson.student_id == user_id, Lesson.tutor_id == user_id)
    )
    if status:
        stmt = stmt.where(Lesson.status == status)
    stmt = stmt.order_by(Lesson.scheduled_start.desc())
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def save(db: AsyncSession, lesson: Lesson) -> Lesson:
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def add_homework(db: AsyncSession, lesson_id: uuid.UUID, data: dict) -> Homework:
    hw = Homework(lesson_id=lesson_id, **data)
    db.add(hw)
    await db.commit()
    await db.refresh(hw)
    return hw


async def get_homework(db: AsyncSession, homework_id: uuid.UUID) -> Homework | None:
    return await db.get(Homework, homework_id)


async def save_homework(db: AsyncSession, hw: Homework) -> Homework:
    await db.commit()
    await db.refresh(hw)
    return hw
