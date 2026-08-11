"""Lesson/calendar endpoints (namespaced under /calendar).

A tutor schedules lessons only inside their own course (verified against the
academics department — see ``services/academics_client.py``); admin/
super_admin can schedule inside any course. Conflict checking and weekly
recurrence are handled entirely inside this department's own ``lessons``
table — no further cross-service call is needed once the course/teacher
relationship is confirmed once at creation time (``teacher_id`` is
denormalized onto the row).

Every lesson gets its own Zoom meeting, created on the *teacher's own*
linked Zoom account (see ``services/zoom_oauth.py``/``zoom_client.py``) —
there is no shared platform Zoom login. If the teacher hasn't connected
Zoom, or Zoom's API is unreachable, lesson creation fails outright rather
than silently scheduling a lesson with no way to actually meet.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role
from edubridge_shared.security import ACCESS_TOKEN_TYPE, TokenError, decode_token

from ...core.config import get_settings
from ...crud import lesson as crud
from ...crud import zoom_account as zoom_account_crud
from ...db.session import get_db
from ...models.lesson import Lesson
from ...models.zoom_account import ZoomAccount
from ...schemas.lesson import (
    LessonCreate,
    LessonOut,
    LessonUpdate,
    ZoomAuthorizeUrl,
    ZoomStatus,
)
from ...services import academics_client, zoom_client, zoom_oauth
from ...services.academics_client import ServiceError
from ...services.ics import render_ics
from ...services.zoom_client import ZoomError
from ...services.zoom_oauth import ZoomOAuthError
from ..deps import get_current_user, require_roles

log = logging.getLogger("calendar")

router = APIRouter(prefix="/calendar", tags=["calendar"])
require_staff = require_roles(Role.ADMIN, Role.SUPER_ADMIN)
require_scheduler = require_roles(Role.TUTOR, Role.ADMIN, Role.SUPER_ADMIN)
require_tutor = require_roles(Role.TUTOR)
_settings = get_settings()


def _bearer(authorization: str = Header(...)) -> str:
    return authorization.removeprefix("Bearer ").strip()


def _user_from_token(token: str) -> CurrentUser:
    try:
        payload = decode_token(
            token,
            secret_key=_settings.jwt_public_key,
            algorithm=_settings.jwt_algorithm,
            expected_type=ACCESS_TOKEN_TYPE,
        )
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return CurrentUser(user_id=payload.sub, role=payload.role)


async def _authorize_teacher(course_id: uuid.UUID, user: CurrentUser, token: str) -> uuid.UUID:
    """Staff can schedule into any course; a tutor only their own. Returns
    the course's teacher_id, to denormalize onto the new Lesson row(s)."""
    try:
        course = await academics_client.get_course(course_id, token)
    except ServiceError as exc:
        if exc.status == 404:
            raise HTTPException(status_code=404, detail="Course not found") from exc
        if exc.status == 403:
            # academics itself 403s a tutor who isn't this course's teacher
            # (or a student who isn't enrolled) — forward that verdict
            # instead of masking it as a generic upstream failure.
            raise HTTPException(status_code=403, detail="Not your course") from exc
        raise HTTPException(status_code=502, detail="Could not verify course") from exc

    teacher_id = course.get("teacher_id")
    if user.role in (Role.ADMIN.value, Role.SUPER_ADMIN.value):
        if teacher_id is None:
            raise HTTPException(status_code=409, detail="Course has no teacher assigned yet")
        return uuid.UUID(teacher_id)
    if teacher_id is None or teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Not your course")
    return uuid.UUID(teacher_id)


async def _lessons_for(user: CurrentUser, token: str, db: AsyncSession) -> list[Lesson]:
    if user.role == Role.TUTOR.value:
        return await crud.list_for_teacher(db, uuid.UUID(user.id))
    if user.role == Role.STUDENT.value:
        course_ids = await academics_client.my_course_ids(token)
        return await crud.list_for_courses(db, course_ids)
    raise HTTPException(status_code=403, detail="Not allowed")


def _authorize_owner(teacher_id: uuid.UUID, user: CurrentUser) -> None:
    if user.role in (Role.ADMIN.value, Role.SUPER_ADMIN.value):
        return
    if user.role == Role.TUTOR.value and str(teacher_id) == user.id:
        return
    raise HTTPException(status_code=403, detail="Not allowed")


def _lesson_out(lesson: Lesson, user: CurrentUser) -> LessonOut:
    """start_url is a host-only link — blanked out for anyone but the
    lesson's own teacher or staff, even though it's stored on every row."""
    out = LessonOut.model_validate(lesson)
    is_owner_or_staff = user.role in (Role.ADMIN.value, Role.SUPER_ADMIN.value) or str(
        lesson.teacher_id
    ) == user.id
    if not is_owner_or_staff:
        out.start_url = None
    return out


async def _zoom_account_or_409(db: AsyncSession, teacher_id: uuid.UUID) -> ZoomAccount:
    account = await zoom_account_crud.get_for_tutor(db, teacher_id)
    if account is None:
        raise HTTPException(
            status_code=409,
            detail="This course's teacher hasn't connected a Zoom account yet",
        )
    return account


# ------------------------------- Lessons --------------------------------


@router.post("/lessons", response_model=list[LessonOut], status_code=status.HTTP_201_CREATED)
async def create_lesson(
    payload: LessonCreate,
    user: CurrentUser = Depends(require_scheduler),
    token: str = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> list[LessonOut]:
    teacher_id = await _authorize_teacher(payload.course_id, user, token)

    if payload.recurrence == "weekly":
        if not payload.recurrence_weeks:
            raise HTTPException(status_code=400, detail="recurrence_weeks is required for weekly recurrence")
        if payload.recurrence_weeks > _settings.max_recurrence_weeks:
            raise HTTPException(
                status_code=400,
                detail=f"recurrence_weeks can't exceed {_settings.max_recurrence_weeks}",
            )
        count = payload.recurrence_weeks
    else:
        count = 1

    duration = timedelta(minutes=payload.duration_minutes)
    occurrences = [
        (
            payload.scheduled_start + timedelta(weeks=i),
            payload.scheduled_start + timedelta(weeks=i) + duration,
        )
        for i in range(count)
    ]

    conflicts = []
    for start, end in occurrences:
        existing = await crud.find_conflict(db, teacher_id, start, end)
        if existing is not None:
            conflicts.append({"scheduled_start": start.isoformat(), "conflicts_with": str(existing.id)})
    if conflicts:
        raise HTTPException(
            status_code=409,
            detail={"message": "Time conflict with an existing lesson", "conflicts": conflicts},
        )

    # Every instance gets its own Zoom meeting, created on the teacher's own
    # linked account — this is a hard prerequisite, not best-effort: a
    # lesson nobody can actually join isn't a useful thing to create.
    zoom_account = await _zoom_account_or_409(db, teacher_id)
    access_token = await _zoom_token_or_502(db, zoom_account)

    created_meetings: list[dict] = []
    try:
        for start, _end in occurrences:
            meeting = await zoom_client.create_meeting(
                access_token, topic="Урок", start=start, duration_minutes=payload.duration_minutes
            )
            created_meetings.append(meeting)
    except ZoomError as exc:
        for meeting in created_meetings:
            try:
                await zoom_client.delete_meeting(access_token, meeting["id"])
            except ZoomError:
                log.warning("Could not clean up orphaned Zoom meeting %s after a failed create", meeting["id"])
        raise HTTPException(status_code=502, detail=f"Could not create Zoom meeting: {exc.detail}") from exc

    series_id = uuid.uuid4() if count > 1 else None
    lessons = [
        Lesson(
            course_id=payload.course_id,
            teacher_id=teacher_id,
            series_id=series_id,
            scheduled_start=start,
            scheduled_end=end,
            zoom_meeting_id=meeting["id"],
            meeting_url=meeting["join_url"],
            start_url=meeting["start_url"],
        )
        for (start, end), meeting in zip(occurrences, created_meetings)
    ]
    created = await crud.create_many(db, lessons)
    return [_lesson_out(l, user) for l in created]


async def _zoom_token_or_502(db: AsyncSession, account: ZoomAccount) -> str:
    try:
        return await zoom_client.ensure_fresh_token(db, account)
    except ZoomError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Zoom: {exc.detail}") from exc


@router.get("/lessons/me", response_model=list[LessonOut])
async def my_lessons(
    user: CurrentUser = Depends(get_current_user),
    token: str = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> list[LessonOut]:
    lessons = await _lessons_for(user, token, db)
    return [_lesson_out(l, user) for l in lessons]


@router.get("/lessons/me.ics")
async def my_lessons_ics(
    token: str = Query(..., description="Access token — this URL is meant to be pasted into an external calendar app, which can't send an Authorization header, so it's authorized by query param instead."),
    db: AsyncSession = Depends(get_db),
) -> Response:
    user = _user_from_token(token)
    lessons = await _lessons_for(user, token, db)
    return Response(content=render_ics(lessons), media_type="text/calendar")


@router.get("/lessons", response_model=list[LessonOut])
async def list_lessons(
    course_id: uuid.UUID | None = Query(default=None),
    teacher_id: uuid.UUID | None = Query(default=None),
    user: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[LessonOut]:
    lessons = await crud.list_query(db, course_id=course_id, teacher_id=teacher_id)
    return [_lesson_out(l, user) for l in lessons]


async def _lesson_or_404(db: AsyncSession, lesson_id: uuid.UUID) -> Lesson:
    lesson = await crud.get(db, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
async def update_lesson(
    lesson_id: uuid.UUID,
    payload: LessonUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    lesson = await _lesson_or_404(db, lesson_id)
    _authorize_owner(lesson.teacher_id, user)

    data = payload.model_dump(exclude_unset=True)
    new_start = data.pop("scheduled_start", None) or lesson.scheduled_start
    duration_minutes = data.pop("duration_minutes", None)
    new_end = (
        new_start + (lesson.scheduled_end - lesson.scheduled_start)
        if duration_minutes is None
        else new_start + timedelta(minutes=duration_minutes)
    )
    time_changed = new_start != lesson.scheduled_start or new_end != lesson.scheduled_end
    if time_changed:
        conflict = await crud.find_conflict(db, lesson.teacher_id, new_start, new_end, exclude_id=lesson.id)
        if conflict is not None:
            raise HTTPException(status_code=409, detail=f"Time conflict with lesson {conflict.id}")
        data["scheduled_start"] = new_start
        data["scheduled_end"] = new_end

    # Reflecting the new time on the Zoom side is best-effort: the hard-fail
    # policy is specifically about *creating* a lesson nobody could join —
    # a reschedule that can't reach Zoom shouldn't strand the local change.
    if time_changed and lesson.zoom_meeting_id:
        account = await zoom_account_crud.get_for_tutor(db, lesson.teacher_id)
        if account is not None:
            try:
                access_token = await zoom_client.ensure_fresh_token(db, account)
                duration = int((new_end - new_start).total_seconds() // 60)
                await zoom_client.update_meeting(access_token, lesson.zoom_meeting_id, start=new_start, duration_minutes=duration)
            except ZoomError as exc:
                log.warning("Could not update Zoom meeting %s for lesson %s: %s", lesson.zoom_meeting_id, lesson.id, exc)

    lesson = await crud.update(db, lesson, data)
    return _lesson_out(lesson, user)


async def _delete_zoom_meeting_best_effort(db: AsyncSession, lesson: Lesson) -> None:
    if not lesson.zoom_meeting_id:
        return
    account = await zoom_account_crud.get_for_tutor(db, lesson.teacher_id)
    if account is None:
        return
    try:
        access_token = await zoom_client.ensure_fresh_token(db, account)
        await zoom_client.delete_meeting(access_token, lesson.zoom_meeting_id)
    except ZoomError as exc:
        log.warning("Could not delete Zoom meeting %s for lesson %s: %s", lesson.zoom_meeting_id, lesson.id, exc)


@router.delete("/lessons/{lesson_id}", status_code=204, response_class=Response)
async def delete_lesson(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    lesson = await _lesson_or_404(db, lesson_id)
    _authorize_owner(lesson.teacher_id, user)
    await _delete_zoom_meeting_best_effort(db, lesson)
    await crud.delete(db, lesson)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/series/{series_id}", status_code=204, response_class=Response)
async def delete_series(
    series_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    series = await crud.list_for_series(db, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    _authorize_owner(series[0].teacher_id, user)
    for lesson in series:
        await _delete_zoom_meeting_best_effort(db, lesson)
    await crud.delete_series(db, series_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------- Zoom ----------------------------------


@router.get("/zoom/connect", response_model=ZoomAuthorizeUrl)
async def zoom_connect(user: CurrentUser = Depends(require_tutor)) -> ZoomAuthorizeUrl:
    try:
        return ZoomAuthorizeUrl(authorize_url=zoom_oauth.authorize_url(user.id))
    except ZoomOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/zoom/callback", include_in_schema=False)
async def zoom_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Zoom redirects the tutor's browser here after they approve (or deny)
    access — there's no Authorization header available, so identity travels
    entirely through the signed ``state`` token minted by /zoom/connect."""
    if error or not code or not state:
        return RedirectResponse(f"{_settings.frontend_url}/dashboard/settings?zoom=error")
    try:
        tutor_id = zoom_oauth.read_state(state)
        token_response = await zoom_oauth.exchange_code(code)
        email = await zoom_oauth.fetch_email(token_response["access_token"])
        await zoom_account_crud.upsert(
            db,
            uuid.UUID(tutor_id),
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            token_expires_at=zoom_oauth.expires_at_from(token_response),
            zoom_email=email,
        )
    except (ZoomOAuthError, ValueError) as exc:
        log.warning("Zoom OAuth callback failed: %s", exc)
        return RedirectResponse(f"{_settings.frontend_url}/dashboard/settings?zoom=error")
    return RedirectResponse(f"{_settings.frontend_url}/dashboard/settings?zoom=connected")


@router.get("/zoom/status", response_model=ZoomStatus)
async def zoom_status(
    user: CurrentUser = Depends(require_tutor), db: AsyncSession = Depends(get_db)
) -> ZoomStatus:
    account = await zoom_account_crud.get_for_tutor(db, uuid.UUID(user.id))
    if account is None:
        return ZoomStatus(connected=False)
    return ZoomStatus(connected=True, email=account.zoom_email)


@router.delete("/zoom", status_code=204, response_class=Response)
async def zoom_disconnect(
    user: CurrentUser = Depends(require_tutor), db: AsyncSession = Depends(get_db)
) -> Response:
    await zoom_account_crud.delete_for_tutor(db, uuid.UUID(user.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
