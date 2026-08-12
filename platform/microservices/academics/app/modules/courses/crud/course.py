"""Course + enrollment persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.course import Course, Enrollment


async def create(
    db: AsyncSession, title: str, description: str | None, category_id: uuid.UUID | None = None
) -> Course:
    course = Course(title=title, description=description, category_id=category_id)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def get(db: AsyncSession, course_id: uuid.UUID) -> Course | None:
    return await db.get(Course, course_id)


async def list_all(db: AsyncSession, limit: int, offset: int) -> list[Course]:
    stmt = select(Course).order_by(Course.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_for_teacher(db: AsyncSession, teacher_id: uuid.UUID) -> list[Course]:
    stmt = select(Course).where(Course.teacher_id == teacher_id).order_by(Course.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_for_student(db: AsyncSession, student_id: uuid.UUID) -> list[Course]:
    stmt = (
        select(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .where(Enrollment.student_id == student_id)
        .order_by(Course.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update(db: AsyncSession, course: Course, data: dict) -> Course:
    for field, value in data.items():
        setattr(course, field, value)
    await db.commit()
    await db.refresh(course)
    return course


async def set_teacher(db: AsyncSession, course: Course, teacher_id: uuid.UUID | None) -> Course:
    course.teacher_id = teacher_id
    await db.commit()
    await db.refresh(course)
    return course


async def delete(db: AsyncSession, course: Course) -> None:
    await db.delete(course)
    await db.commit()


async def student_ids(db: AsyncSession, course_id: uuid.UUID) -> list[uuid.UUID]:
    result = await db.execute(select(Enrollment.student_id).where(Enrollment.course_id == course_id))
    return list(result.scalars().all())


async def is_enrolled(db: AsyncSession, course_id: uuid.UUID, student_id: uuid.UUID) -> bool:
    stmt = select(Enrollment.id).where(
        Enrollment.course_id == course_id, Enrollment.student_id == student_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def enroll(db: AsyncSession, course_id: uuid.UUID, student_id: uuid.UUID) -> Enrollment:
    enrollment = Enrollment(course_id=course_id, student_id=student_id)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def unenroll(db: AsyncSession, course_id: uuid.UUID, student_id: uuid.UUID) -> bool:
    result = await db.execute(
        sa_delete(Enrollment).where(
            Enrollment.course_id == course_id, Enrollment.student_id == student_id
        )
    )
    await db.commit()
    return result.rowcount > 0
