"""Homework persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.homework import Homework, HomeworkStatus


async def create(db: AsyncSession, homework: Homework) -> Homework:
    if homework.grade is not None:
        homework.status = HomeworkStatus.GRADED.value
        homework.graded_at = datetime.now(timezone.utc)
    db.add(homework)
    await db.commit()
    await db.refresh(homework)
    return homework


async def get(db: AsyncSession, homework_id: uuid.UUID) -> Homework | None:
    return await db.get(Homework, homework_id)


async def list_for_student(db: AsyncSession, student_id: uuid.UUID, course_id: uuid.UUID | None) -> list[Homework]:
    stmt = select(Homework).where(Homework.student_id == student_id)
    if course_id is not None:
        stmt = stmt.where(Homework.course_id == course_id)
    stmt = stmt.order_by(Homework.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_for_teacher(
    db: AsyncSession, teacher_id: uuid.UUID, course_id: uuid.UUID | None, lesson_id: uuid.UUID | None
) -> list[Homework]:
    stmt = select(Homework).where(Homework.teacher_id == teacher_id)
    if course_id is not None:
        stmt = stmt.where(Homework.course_id == course_id)
    if lesson_id is not None:
        stmt = stmt.where(Homework.lesson_id == lesson_id)
    stmt = stmt.order_by(Homework.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def submit(db: AsyncSession, homework: Homework, submission_url: str, submission_note: str | None) -> Homework:
    homework.submission_url = submission_url
    homework.submission_note = submission_note
    homework.submitted_at = datetime.now(timezone.utc)
    if homework.status == HomeworkStatus.ASSIGNED.value:
        homework.status = HomeworkStatus.SUBMITTED.value
    await db.commit()
    await db.refresh(homework)
    return homework


async def grade(db: AsyncSession, homework: Homework, grade: float, comment: str | None) -> Homework:
    homework.grade = grade
    homework.comment = comment
    homework.graded_at = datetime.now(timezone.utc)
    homework.status = HomeworkStatus.GRADED.value
    await db.commit()
    await db.refresh(homework)
    return homework
