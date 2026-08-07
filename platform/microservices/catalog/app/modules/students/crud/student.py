"""Database access for students, favorites, progress and intake leads."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.student import FavoriteTutor, LearningProgress, Student, StudentLead


async def get_or_create(db: AsyncSession, user_id: uuid.UUID) -> Student:
    student = await db.get(Student, user_id)
    if student is None:
        student = Student(user_id=user_id, learning_languages=[])
        db.add(student)
        await db.commit()
        await db.refresh(student)
    return student


async def update(db: AsyncSession, student: Student, data: dict) -> Student:
    for field, value in data.items():
        setattr(student, field, value)
    await db.commit()
    await db.refresh(student)
    return student


async def add_favorite(
    db: AsyncSession, student_id: uuid.UUID, tutor_id: uuid.UUID
) -> FavoriteTutor:
    existing = await db.execute(
        select(FavoriteTutor).where(
            FavoriteTutor.student_id == student_id,
            FavoriteTutor.tutor_id == tutor_id,
        )
    )
    fav = existing.scalar_one_or_none()
    if fav is not None:
        return fav
    fav = FavoriteTutor(student_id=student_id, tutor_id=tutor_id)
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return fav


async def remove_favorite(
    db: AsyncSession, student_id: uuid.UUID, tutor_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(FavoriteTutor).where(
            FavoriteTutor.student_id == student_id,
            FavoriteTutor.tutor_id == tutor_id,
        )
    )
    fav = result.scalar_one_or_none()
    if fav is None:
        return False
    await db.delete(fav)
    await db.commit()
    return True


async def upsert_progress(
    db: AsyncSession, student_id: uuid.UUID, data: dict
) -> LearningProgress:
    result = await db.execute(
        select(LearningProgress).where(
            LearningProgress.student_id == student_id,
            LearningProgress.subject == data["subject"],
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        entry = LearningProgress(student_id=student_id, **data)
        db.add(entry)
    else:
        for field, value in data.items():
            setattr(entry, field, value)
    await db.commit()
    await db.refresh(entry)
    return entry


async def create_lead(db: AsyncSession, data: dict) -> StudentLead:
    lead = StudentLead(**data)
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead


async def list_leads(db: AsyncSession, limit: int = 200) -> list[StudentLead]:
    result = await db.execute(
        select(StudentLead).order_by(StudentLead.created_at.desc()).limit(limit)
    )
    return list(result.scalars())
