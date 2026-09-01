"""Lesson persistence, including the teacher-conflict check."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, delete as sa_delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.lesson import Lesson, LessonStatus


async def find_conflict(
    db: AsyncSession,
    teacher_id: uuid.UUID,
    start: datetime,
    end: datetime,
    *,
    exclude_id: uuid.UUID | None = None,
) -> Lesson | None:
    """First existing (non-cancelled) lesson for this teacher whose time
    range overlaps [start, end) — two intervals overlap iff each starts
    before the other ends."""
    stmt = select(Lesson).where(
        Lesson.teacher_id == teacher_id,
        Lesson.status != LessonStatus.CANCELLED.value,
        Lesson.scheduled_start < end,
        Lesson.scheduled_end > start,
    )
    if exclude_id is not None:
        stmt = stmt.where(Lesson.id != exclude_id)
    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none()


async def list_for_teacher_on_day(db: AsyncSession, teacher_id: uuid.UUID, day: datetime) -> list[Lesson]:
    """Every non-cancelled lesson this teacher has on `day`'s calendar date
    (UTC) — used to let a scheduling-conflict response suggest real free
    slots instead of just failing (see routes/calendar.py::create_lesson)."""
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    stmt = (
        select(Lesson)
        .where(
            Lesson.teacher_id == teacher_id,
            Lesson.status != LessonStatus.CANCELLED.value,
            Lesson.scheduled_start >= day_start,
            Lesson.scheduled_start < day_end,
        )
        .order_by(Lesson.scheduled_start)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_many(db: AsyncSession, lessons: list[Lesson]) -> list[Lesson]:
    db.add_all(lessons)
    await db.commit()
    for lesson in lessons:
        await db.refresh(lesson)
    return lessons


async def get(db: AsyncSession, lesson_id: uuid.UUID) -> Lesson | None:
    return await db.get(Lesson, lesson_id)


async def list_for_teacher(db: AsyncSession, teacher_id: uuid.UUID) -> list[Lesson]:
    stmt = select(Lesson).where(Lesson.teacher_id == teacher_id).order_by(Lesson.scheduled_start)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_for_series(db: AsyncSession, series_id: uuid.UUID) -> list[Lesson]:
    stmt = select(Lesson).where(Lesson.series_id == series_id).order_by(Lesson.scheduled_start)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_for_courses(
    db: AsyncSession, course_ids: list[uuid.UUID], *, student_id: uuid.UUID
) -> list[Lesson]:
    """A student's own feed: every whole-group lesson in a course they're
    enrolled in, plus only their own individual (student_id-targeted)
    lessons — never another student's 1:1 lesson in the same course."""
    if not course_ids:
        return []
    stmt = (
        select(Lesson)
        .where(
            Lesson.course_id.in_(course_ids),
            or_(Lesson.student_id.is_(None), Lesson.student_id == student_id),
        )
        .order_by(Lesson.scheduled_start)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_query(
    db: AsyncSession, *, course_id: uuid.UUID | None, teacher_id: uuid.UUID | None
) -> list[Lesson]:
    conditions = []
    if course_id is not None:
        conditions.append(Lesson.course_id == course_id)
    if teacher_id is not None:
        conditions.append(Lesson.teacher_id == teacher_id)
    stmt = select(Lesson).where(and_(*conditions)).order_by(Lesson.scheduled_start) if conditions else (
        select(Lesson).order_by(Lesson.scheduled_start)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update(db: AsyncSession, lesson: Lesson, data: dict) -> Lesson:
    for field, value in data.items():
        setattr(lesson, field, value)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def delete(db: AsyncSession, lesson: Lesson) -> None:
    await db.delete(lesson)
    await db.commit()


async def delete_series(db: AsyncSession, series_id: uuid.UUID) -> int:
    result = await db.execute(sa_delete(Lesson).where(Lesson.series_id == series_id))
    await db.commit()
    return result.rowcount
