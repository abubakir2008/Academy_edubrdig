"""Course endpoints (namespaced under /courses).

Full CRUD (create/update/delete/assign teacher/manage roster) is
super_admin-only. ``admin`` can list and read but never mutates. ``tutor``
and ``student`` only ever see their own courses, via ``/courses/me`` and
``/courses/{id}`` (which 403s if they're not the assigned teacher / an
enrolled student) — this is also what the ``calendar`` department calls,
forwarding the caller's own token, to authorize lesson scheduling.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import course as crud
from ...db.session import get_db
from ...models.course import Course
from ...schemas.course import (
    CourseCreate,
    CourseDetail,
    CourseOut,
    CourseUpdate,
    EnrollmentCreate,
    TeacherAssign,
)
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/courses", tags=["courses"])
require_super_admin = require_roles(Role.SUPER_ADMIN)
require_staff = require_roles(Role.ADMIN, Role.SUPER_ADMIN)


async def _to_detail(db: AsyncSession, course: Course) -> CourseDetail:
    ids = await crud.student_ids(db, course.id)
    return CourseDetail(**CourseOut.model_validate(course).model_dump(), student_ids=ids)


async def _course_or_404(db: AsyncSession, course_id: uuid.UUID) -> Course:
    course = await crud.get(db, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


async def _authorize_view(db: AsyncSession, course: Course, user: CurrentUser) -> None:
    """Staff can view any course; a tutor only their own, a student only one
    they're enrolled in — matches the table in the courses feature plan."""
    if user.role in (Role.ADMIN.value, Role.SUPER_ADMIN.value):
        return
    if user.role == Role.TUTOR.value and course.teacher_id == uuid.UUID(user.id):
        return
    if user.role == Role.STUDENT.value and await crud.is_enrolled(db, course.id, uuid.UUID(user.id)):
        return
    raise HTTPException(status_code=403, detail="Not allowed")


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> CourseOut:
    course = await crud.create(db, payload.title, payload.description)
    return CourseOut.model_validate(course)


@router.get("", response_model=list[CourseOut])
async def list_courses(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    _: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[CourseOut]:
    courses = await crud.list_all(db, limit, offset)
    return [CourseOut.model_validate(c) for c in courses]


@router.get("/me", response_model=list[CourseOut])
async def my_courses(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CourseOut]:
    if user.role == Role.TUTOR.value:
        courses = await crud.list_for_teacher(db, uuid.UUID(user.id))
    elif user.role == Role.STUDENT.value:
        courses = await crud.list_for_student(db, uuid.UUID(user.id))
    else:
        raise HTTPException(status_code=403, detail="Not allowed")
    return [CourseOut.model_validate(c) for c in courses]


@router.get("/{course_id}", response_model=CourseDetail)
async def get_course(
    course_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    course = await _course_or_404(db, course_id)
    await _authorize_view(db, course, user)
    return await _to_detail(db, course)


@router.put("/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> CourseOut:
    course = await _course_or_404(db, course_id)
    course = await crud.update(db, course, payload.model_dump(exclude_unset=True))
    return CourseOut.model_validate(course)


@router.delete("/{course_id}", status_code=204, response_class=Response)
async def delete_course(
    course_id: uuid.UUID,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    course = await _course_or_404(db, course_id)
    await crud.delete(db, course)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{course_id}/teacher", response_model=CourseOut)
async def assign_teacher(
    course_id: uuid.UUID,
    payload: TeacherAssign,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> CourseOut:
    course = await _course_or_404(db, course_id)
    course = await crud.set_teacher(db, course, payload.teacher_id)
    return CourseOut.model_validate(course)


@router.post("/{course_id}/students", response_model=CourseDetail, status_code=201)
async def add_student(
    course_id: uuid.UUID,
    payload: EnrollmentCreate,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    course = await _course_or_404(db, course_id)
    if await crud.is_enrolled(db, course_id, payload.student_id):
        raise HTTPException(status_code=409, detail="Student already enrolled")
    await crud.enroll(db, course_id, payload.student_id)
    return await _to_detail(db, course)


@router.delete("/{course_id}/students/{student_id}", response_model=CourseDetail)
async def remove_student(
    course_id: uuid.UUID,
    student_id: uuid.UUID,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    course = await _course_or_404(db, course_id)
    removed = await crud.unenroll(db, course_id, student_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Student not enrolled")
    return await _to_detail(db, course)
