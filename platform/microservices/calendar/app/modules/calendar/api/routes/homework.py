"""Homework endpoints (namespaced under /calendar), tied to a lesson.

A teacher grades/assigns homework for one student at a time (see
models/homework.py's docstring for why) — right after a lesson if they
like, or later. A student submits their own work and sees only their own
homework; a teacher sees what they've assigned.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import homework as crud
from ...db.session import get_db
from ...models.homework import Homework
from ...schemas.homework import HomeworkCreate, HomeworkGrade, HomeworkOut, HomeworkSubmit
from ...services import academics_client, notifications_client
from ...services.academics_client import ServiceError
from ..deps import get_current_user
from .calendar import _authorize_owner, _bearer, _lesson_or_404

router = APIRouter(prefix="/calendar", tags=["homework"])


async def _homework_or_404(db: AsyncSession, homework_id: uuid.UUID) -> Homework:
    hw = await crud.get(db, homework_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Homework not found")
    return hw


@router.post(
    "/lessons/{lesson_id}/homework", response_model=HomeworkOut, status_code=status.HTTP_201_CREATED
)
async def create_homework(
    lesson_id: uuid.UUID,
    payload: HomeworkCreate,
    user: CurrentUser = Depends(get_current_user),
    token: str = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> HomeworkOut:
    lesson = await _lesson_or_404(db, lesson_id)
    _authorize_owner(lesson.teacher_id, user)

    if lesson.student_id is not None:
        if payload.student_id != lesson.student_id:
            raise HTTPException(status_code=400, detail="This lesson is only for its own assigned student")
    else:
        try:
            course = await academics_client.get_course(lesson.course_id, token)
        except ServiceError as exc:
            raise HTTPException(status_code=502, detail="Could not verify roster") from exc
        if str(payload.student_id) not in course.get("student_ids", []):
            raise HTTPException(status_code=400, detail="Student is not enrolled in this course")

    homework = Homework(
        lesson_id=lesson.id,
        course_id=lesson.course_id,
        teacher_id=lesson.teacher_id,
        student_id=payload.student_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        grade=payload.grade,
        comment=payload.comment,
    )
    created = await crud.create(db, homework)
    await notifications_client.notify(
        str(created.student_id),
        type="homework_assigned",
        title="Новое домашнее задание",
        body=created.title,
    )
    return HomeworkOut.model_validate(created)


@router.get("/lessons/{lesson_id}/homework", response_model=list[HomeworkOut])
async def list_lesson_homework(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HomeworkOut]:
    lesson = await _lesson_or_404(db, lesson_id)
    _authorize_owner(lesson.teacher_id, user)
    items = await crud.list_for_teacher(db, lesson.teacher_id, course_id=None, lesson_id=lesson.id)
    return [HomeworkOut.model_validate(h) for h in items]


@router.get("/homework/me", response_model=list[HomeworkOut])
async def my_homework(
    course_id: uuid.UUID | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[HomeworkOut]:
    if user.role == Role.STUDENT.value:
        items = await crud.list_for_student(db, uuid.UUID(user.id), course_id)
    elif user.role == Role.TUTOR.value:
        items = await crud.list_for_teacher(db, uuid.UUID(user.id), course_id, lesson_id=None)
    else:
        raise HTTPException(status_code=403, detail="Not allowed")
    return [HomeworkOut.model_validate(h) for h in items]


@router.post("/homework/{homework_id}/submit", response_model=HomeworkOut)
async def submit_homework(
    homework_id: uuid.UUID,
    payload: HomeworkSubmit,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkOut:
    hw = await _homework_or_404(db, homework_id)
    if str(hw.student_id) != user.id:
        raise HTTPException(status_code=403, detail="Not your homework")
    updated = await crud.submit(db, hw, payload.submission_url, payload.submission_note)
    return HomeworkOut.model_validate(updated)


@router.put("/homework/{homework_id}/grade", response_model=HomeworkOut)
async def grade_homework(
    homework_id: uuid.UUID,
    payload: HomeworkGrade,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkOut:
    hw = await _homework_or_404(db, homework_id)
    _authorize_owner(hw.teacher_id, user)
    updated = await crud.grade(db, hw, payload.grade, payload.comment)
    await notifications_client.notify(
        str(updated.student_id),
        type="homework_graded",
        title="Домашнее задание проверено",
        body=f"{updated.title} — оценка {updated.grade}",
    )
    return HomeworkOut.model_validate(updated)
