"""Lesson & homework endpoints (namespaced under /lessons)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.events import Topics
from edubridge_shared.fastapi_auth import CurrentUser

from ...crud import lesson as crud
from ...db.session import get_db
from ...events import bus
from ...models.lesson import HomeworkStatus, LessonStatus
from ...schemas.lesson import (
    HomeworkCreate,
    HomeworkGrade,
    HomeworkOut,
    HomeworkSubmit,
    LessonCreate,
    LessonOut,
    NotesUpdate,
    RecordingUpdate,
)
from ..deps import get_current_user

router = APIRouter(prefix="/lessons", tags=["lessons"])


def _uid(user: CurrentUser) -> uuid.UUID:
    return uuid.UUID(user.id)


async def _get_participant(db, lesson_id, uid):
    lesson = await crud.get(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if uid not in (lesson.student_id, lesson.tutor_id):
        raise HTTPException(status_code=403, detail="Not your lesson")
    return lesson


@router.post("", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    payload: LessonCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    lesson = await crud.create(db, payload.model_dump())
    return LessonOut.model_validate(lesson)


@router.get("/me", response_model=list[LessonOut])
async def my_lessons(
    status_filter: str | None = Query(default=None, alias="status"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LessonOut]:
    items = await crud.list_for_user(db, _uid(user), status_filter)
    return [LessonOut.model_validate(x) for x in items]


@router.get("/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    lesson = await _get_participant(db, lesson_id, _uid(user))
    return LessonOut.model_validate(lesson)


@router.post("/{lesson_id}/start", response_model=LessonOut)
async def start_lesson(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    lesson = await _get_participant(db, lesson_id, _uid(user))
    lesson.status = LessonStatus.IN_PROGRESS.value
    lesson.started_at = datetime.now(tz=timezone.utc)
    return LessonOut.model_validate(await crud.save(db, lesson))


@router.post("/{lesson_id}/complete", response_model=LessonOut)
async def complete_lesson(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    lesson = await _get_participant(db, lesson_id, _uid(user))
    lesson.status = LessonStatus.COMPLETED.value
    lesson.ended_at = datetime.now(tz=timezone.utc)
    saved = await crud.save(db, lesson)
    # Prompts a review request + analytics + tutor stats downstream.
    await bus.publish(
        Topics.LESSON_COMPLETED,
        {
            "lesson_id": str(saved.id),
            "student_id": str(saved.student_id),
            "tutor_id": str(saved.tutor_id),
        },
        key=str(saved.tutor_id),
    )
    return LessonOut.model_validate(saved)


@router.put("/{lesson_id}/notes", response_model=LessonOut)
async def update_notes(
    lesson_id: uuid.UUID,
    payload: NotesUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    lesson = await _get_participant(db, lesson_id, _uid(user))
    uid = _uid(user)
    # Tutor edits tutor_notes, student edits student_notes.
    if payload.tutor_notes is not None and uid == lesson.tutor_id:
        lesson.tutor_notes = payload.tutor_notes
    if payload.student_notes is not None and uid == lesson.student_id:
        lesson.student_notes = payload.student_notes
    return LessonOut.model_validate(await crud.save(db, lesson))


@router.put("/{lesson_id}/recording", response_model=LessonOut)
async def set_recording(
    lesson_id: uuid.UUID,
    payload: RecordingUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    lesson = await _get_participant(db, lesson_id, _uid(user))
    lesson.recording_url = payload.recording_url
    return LessonOut.model_validate(await crud.save(db, lesson))


# ------------------------------ Homework -------------------------------

@router.post("/{lesson_id}/homework", response_model=HomeworkOut, status_code=201)
async def assign_homework(
    lesson_id: uuid.UUID,
    payload: HomeworkCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkOut:
    lesson = await _get_participant(db, lesson_id, _uid(user))
    if _uid(user) != lesson.tutor_id:
        raise HTTPException(status_code=403, detail="Only the tutor can assign homework")
    hw = await crud.add_homework(db, lesson_id, payload.model_dump())
    return HomeworkOut.model_validate(hw)


@router.post("/homework/{homework_id}/submit", response_model=HomeworkOut)
async def submit_homework(
    homework_id: uuid.UUID,
    payload: HomeworkSubmit,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkOut:
    hw = await crud.get_homework(db, homework_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Homework not found")
    lesson = await _get_participant(db, hw.lesson_id, _uid(user))
    if _uid(user) != lesson.student_id:
        raise HTTPException(status_code=403, detail="Only the student can submit")
    hw.submission_text = payload.submission_text
    hw.status = HomeworkStatus.SUBMITTED.value
    return HomeworkOut.model_validate(await crud.save_homework(db, hw))


@router.post("/homework/{homework_id}/grade", response_model=HomeworkOut)
async def grade_homework(
    homework_id: uuid.UUID,
    payload: HomeworkGrade,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HomeworkOut:
    hw = await crud.get_homework(db, homework_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Homework not found")
    lesson = await _get_participant(db, hw.lesson_id, _uid(user))
    if _uid(user) != lesson.tutor_id:
        raise HTTPException(status_code=403, detail="Only the tutor can grade")
    hw.grade = payload.grade
    hw.feedback = payload.feedback
    hw.status = HomeworkStatus.GRADED.value
    return HomeworkOut.model_validate(await crud.save_homework(db, hw))
