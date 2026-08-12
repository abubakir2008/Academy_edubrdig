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

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...cache import MY_COURSES_TTL_SECONDS, cache, my_courses_key
from ...crud import category as category_crud
from ...crud import course as crud
from ...db.session import get_db
from ...models.category import Category
from ...models.course import Course
from ...schemas.course import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    CourseCreate,
    CourseDetail,
    CourseOut,
    CourseUpdate,
    EnrollmentCreate,
    TeacherAssign,
)
from ...services import chat_client, identity_client
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/courses", tags=["courses"])
require_super_admin = require_roles(Role.SUPER_ADMIN)
require_staff = require_roles(Role.ADMIN, Role.SUPER_ADMIN)


def _bearer(authorization: str = Header(...)) -> str:
    return authorization.removeprefix("Bearer ").strip()


async def _connect_student_chats(course: Course, student_id: uuid.UUID, token: str) -> None:
    """Auto-create chats so the student can immediately reach their teacher
    and platform admins — see services/chat_client.py. Best-effort: never
    blocks or fails the enrollment itself."""
    student = str(student_id)
    if course.teacher_id is not None:
        await chat_client.ensure_conversation(student, str(course.teacher_id))
    for admin_id in await identity_client.super_admin_ids(token):
        await chat_client.ensure_conversation(student, admin_id)


async def _connect_teacher_chats(db: AsyncSession, course_id: uuid.UUID, teacher_id: uuid.UUID) -> None:
    """Mirror of _connect_student_chats for the other order of events —
    a teacher assigned to a course that already has a roster."""
    for student_id in await crud.student_ids(db, course_id):
        await chat_client.ensure_conversation(str(student_id), str(teacher_id))


async def _invalidate_my_courses(db: AsyncSession, course: Course) -> None:
    """Invalidate every /courses/me cache entry this course could appear in
    — its teacher plus its whole roster."""
    keys = []
    if course.teacher_id is not None:
        keys.append(my_courses_key(course.teacher_id))
    for student_id in await crud.student_ids(db, course.id):
        keys.append(my_courses_key(student_id))
    await cache.delete(*keys)


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
    course = await crud.create(db, payload.title, payload.description, payload.category_id)
    return CourseOut.model_validate(course)


# ------------------------------- Categories -------------------------------
# Plain taxonomy shared by courses and the public tutor listing (a tutor's
# `category_ids` — see identity's profile — references these same ids).
# Public read (the tutor page and course filters need it unauthenticated),
# staff-managed write.


async def _category_or_404(db: AsyncSession, category_id: uuid.UUID) -> Category:
    category = await category_crud.get(db, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[CategoryOut]:
    categories = await category_crud.list_all(db)
    return [CategoryOut.model_validate(c) for c in categories]


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    _: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    category = await category_crud.create(db, payload.name, payload.slug)
    return CategoryOut.model_validate(category)


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    _: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    category = await _category_or_404(db, category_id)
    category = await category_crud.update(db, category, payload.model_dump(exclude_unset=True))
    return CategoryOut.model_validate(category)


@router.delete("/categories/{category_id}", status_code=204, response_class=Response)
async def delete_category(
    category_id: uuid.UUID,
    _: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> Response:
    category = await _category_or_404(db, category_id)
    await category_crud.delete(db, category)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    # 60s cache-aside, keyed per user: this is fetched on nearly every
    # dashboard visit (overview widgets, course pages) and only changes on
    # the handful of admin mutations below, each of which invalidates it.
    key = my_courses_key(user.id)
    cached = await cache.get(key)
    if cached is not None:
        return [CourseOut.model_validate(c) for c in cached]

    if user.role == Role.TUTOR.value:
        courses = await crud.list_for_teacher(db, uuid.UUID(user.id))
    elif user.role == Role.STUDENT.value:
        courses = await crud.list_for_student(db, uuid.UUID(user.id))
    else:
        raise HTTPException(status_code=403, detail="Not allowed")

    result = [CourseOut.model_validate(c) for c in courses]
    await cache.set(key, [c.model_dump(mode="json") for c in result], MY_COURSES_TTL_SECONDS)
    return result


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
    await _invalidate_my_courses(db, course)
    course = await crud.update(db, course, payload.model_dump(exclude_unset=True))
    return CourseOut.model_validate(course)


@router.delete("/{course_id}", status_code=204, response_class=Response)
async def delete_course(
    course_id: uuid.UUID,
    _: CurrentUser = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    course = await _course_or_404(db, course_id)
    await _invalidate_my_courses(db, course)
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
    old_teacher_id = course.teacher_id
    course = await crud.set_teacher(db, course, payload.teacher_id)
    keys = [my_courses_key(t) for t in (old_teacher_id, payload.teacher_id) if t is not None]
    await cache.delete(*keys)
    if payload.teacher_id is not None:
        await _connect_teacher_chats(db, course_id, payload.teacher_id)
    return CourseOut.model_validate(course)


@router.post("/{course_id}/students", response_model=CourseDetail, status_code=201)
async def add_student(
    course_id: uuid.UUID,
    payload: EnrollmentCreate,
    _: CurrentUser = Depends(require_super_admin),
    token: str = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> CourseDetail:
    course = await _course_or_404(db, course_id)
    if await crud.is_enrolled(db, course_id, payload.student_id):
        raise HTTPException(status_code=409, detail="Student already enrolled")
    await crud.enroll(db, course_id, payload.student_id)
    await cache.delete(my_courses_key(payload.student_id))
    await _connect_student_chats(course, payload.student_id, token)
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
    await cache.delete(my_courses_key(student_id))
    return await _to_detail(db, course)
