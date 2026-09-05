"""Lesson/calendar endpoints (namespaced under /calendar).

A tutor schedules lessons only inside their own course (verified against the
academics department — see ``services/academics_client.py``); admin/
super_admin can schedule inside any course. Conflict checking is handled
entirely inside this department's own ``lessons`` table — no further
cross-service call is needed once the course/teacher relationship is
confirmed once at creation time (``teacher_id`` is denormalized onto the row).

Video calls run on LiveKit (see ``services/livekit_client.py``): there's
nothing to create ahead of time the way a Zoom meeting used to be — a
lesson's room is just its id, and ``GET /lessons/{id}/join`` mints a fresh
access token for whoever's allowed to be in it.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role
from edubridge_shared.security import ACCESS_TOKEN_TYPE, TokenError, decode_token

from ...core.config import get_settings
from ...crud import lesson as crud
from ...db.session import get_db
from ...models.lesson import Lesson, LessonStatus
from ...schemas.lesson import LessonCreate, LessonJoin, LessonOut, LessonUpdate, RecordingOut
from ...services import academics_client, livekit_client, recordings
from ...services.academics_client import ServiceError
from ...services.ics import render_ics
from ...services.livekit_client import LiveKitError
from ...services.recordings import RecordingError
from ..deps import get_current_user, require_roles

log = logging.getLogger("calendar")

router = APIRouter(prefix="/calendar", tags=["calendar"])
require_staff = require_roles(Role.ADMIN, Role.SUPER_ADMIN)
require_scheduler = require_roles(Role.TUTOR, Role.ADMIN, Role.SUPER_ADMIN)
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
    the course's teacher_id, to denormalize onto the new Lesson row."""
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
        return await crud.list_for_courses(db, course_ids, student_id=uuid.UUID(user.id))
    raise HTTPException(status_code=403, detail="Not allowed")


def _authorize_owner(teacher_id: uuid.UUID, user: CurrentUser) -> None:
    if user.role in (Role.ADMIN.value, Role.SUPER_ADMIN.value):
        return
    if user.role == Role.TUTOR.value and str(teacher_id) == user.id:
        return
    raise HTTPException(status_code=403, detail="Not allowed")


async def _authorize_participant(lesson: Lesson, user: CurrentUser, token: str) -> None:
    """Who's allowed to see/join a specific lesson: staff, its own teacher,
    or a student enrolled in its course."""
    if user.role in (Role.ADMIN.value, Role.SUPER_ADMIN.value):
        return
    if user.role == Role.TUTOR.value and str(lesson.teacher_id) == user.id:
        return
    if user.role == Role.STUDENT.value:
        if lesson.student_id is not None:
            if str(lesson.student_id) == user.id:
                return
            raise HTTPException(status_code=403, detail="Not allowed")
        course_ids = await academics_client.my_course_ids(token)
        if lesson.course_id in course_ids:
            return
    raise HTTPException(status_code=403, detail="Not allowed")


def _lesson_out(lesson: Lesson, user: CurrentUser) -> LessonOut:
    out = LessonOut.model_validate(lesson)
    # A lesson nobody marked "completed" (or "cancelled") by the time its
    # own end time passes reads as "missed" — computed here on every read,
    # never written back, so there's no cron/background job keeping this in
    # sync: it's just always correct relative to "now".
    if out.status == LessonStatus.SCHEDULED.value and out.scheduled_end < datetime.now(timezone.utc):
        out.status = LessonStatus.MISSED.value
    return out


# ------------------------------- Lessons --------------------------------


@router.post("/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    payload: LessonCreate,
    user: CurrentUser = Depends(require_scheduler),
    token: str = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    teacher_id = await _authorize_teacher(payload.course_id, user, token)

    if payload.student_id is not None:
        try:
            course = await academics_client.get_course(payload.course_id, token)
        except ServiceError as exc:
            raise HTTPException(status_code=502, detail="Could not verify roster") from exc
        if str(payload.student_id) not in course.get("student_ids", []):
            raise HTTPException(status_code=400, detail="Student is not enrolled in this course")

    start = payload.scheduled_start
    end = start + timedelta(minutes=payload.duration_minutes)

    existing = await crud.find_conflict(db, teacher_id, start, end)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Time conflict with an existing lesson",
                "conflicts_with": str(existing.id),
                # Lets the client suggest real free slots instead of just
                # reporting failure — every other lesson this teacher has
                # that same day, so it can compute gaps itself.
                "teacher_lessons_that_day": [
                    {"scheduled_start": l.scheduled_start.isoformat(), "scheduled_end": l.scheduled_end.isoformat()}
                    for l in await crud.list_for_teacher_on_day(db, teacher_id, start)
                ],
            },
        )

    lesson = Lesson(
        course_id=payload.course_id,
        teacher_id=teacher_id,
        student_id=payload.student_id,
        scheduled_start=start,
        scheduled_end=end,
        title=payload.title,
        description=payload.description,
    )
    created = await crud.create_many(db, [lesson])

    # Recording (if configured) isn't attached here — the lesson-recorder
    # service watches for lessons entering their scheduled window on its own
    # and joins the room itself; see platform/lesson-recorder/.
    return _lesson_out(created[0], user)


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


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    token: str = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> LessonOut:
    lesson = await _lesson_or_404(db, lesson_id)
    await _authorize_participant(lesson, user, token)
    return _lesson_out(lesson, user)


@router.get("/lessons/{lesson_id}/join", response_model=LessonJoin)
async def join_lesson(
    lesson_id: uuid.UUID,
    # The frontend already knows the caller's display name (from /auth/me);
    # passing it here means minting a token never needs its own lookup into
    # identity's user profiles just to label a video tile nicely.
    name: str | None = Query(default=None, description="Display name shown on the caller's video tile."),
    user: CurrentUser = Depends(get_current_user),
    token: str = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> LessonJoin:
    lesson = await _lesson_or_404(db, lesson_id)
    await _authorize_participant(lesson, user, token)
    try:
        access_token = livekit_client.mint_token(lesson_id=lesson.id, identity=user.id, name=name or user.id)
    except LiveKitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return LessonJoin(livekit_url=_settings.livekit_url, token=access_token, room=livekit_client.room_name(lesson.id))


@router.get("/lessons/{lesson_id}/recordings", response_model=list[RecordingOut])
async def list_lesson_recordings(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    token: str = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> list[RecordingOut]:
    lesson = await _lesson_or_404(db, lesson_id)
    await _authorize_participant(lesson, user, token)
    items = await recordings.list_recordings(livekit_client.room_name(lesson.id))
    # MinIO isn't reachable from a browser (see recordings.py) — every
    # recording is played back through our own stream route below instead
    # of a presigned link, authorized by the same query-param token as the
    # .ics feed (a <video src> can't send an Authorization header either).
    return [
        RecordingOut(
            **item,
            # `/api` isn't this department's own prefix — it's the gateway's
            # (Traefik strips it before routing here, same as every other
            # request) — but the frontend hands this string straight to
            # `<video src>` with nothing of its own prepended, so it has to
            # be a complete, browser-reachable path, same as the old
            # presigned Backblaze URL this replaces.
            url=f"/api/calendar/lessons/{lesson_id}/recordings/{quote(item['object_name'], safe='')}/stream?token={quote(token)}",
        )
        for item in items
    ]


def _stream_object(resp):
    try:
        yield from resp.stream(64 * 1024)
    finally:
        resp.close()
        resp.release_conn()


@router.get("/lessons/{lesson_id}/recordings/{object_name:path}/stream")
async def stream_lesson_recording(
    request: Request,
    lesson_id: uuid.UUID,
    object_name: str,
    token: str = Query(..., description="Access token — a <video> tag can't send an Authorization header, so it's authorized by query param instead, same as the .ics feed."),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    user = _user_from_token(token)
    lesson = await _lesson_or_404(db, lesson_id)
    await _authorize_participant(lesson, user, token)
    if not object_name.startswith(f"{livekit_client.room_name(lesson.id)}/"):
        raise HTTPException(status_code=404, detail="Recording not found")
    try:
        # Forwarding the browser/ExoPlayer/AVPlayer's own Range header (not
        # just always serving byte 0 onward) is what lets it seek instead of
        # re-downloading the whole recording, and — for anything recorded
        # before lesson-recorder started muxing with +faststart — is the only
        # way playback can start before the full file is in.
        body, status_code, headers = recordings.open_recording(object_name, request.headers.get("range"))
    except RecordingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Recording not found") from exc
    return StreamingResponse(_stream_object(body), status_code=status_code, media_type="video/mp4", headers=headers)


@router.delete("/lessons/{lesson_id}/recordings/{object_name:path}", status_code=204, response_class=Response)
async def delete_lesson_recording(
    lesson_id: uuid.UUID,
    object_name: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    lesson = await _lesson_or_404(db, lesson_id)
    _authorize_owner(lesson.teacher_id, user)
    # The room name is a prefix of every one of its own recordings' object
    # names ("{room_name}/{time}.mp4") — cheap guard against deleting a
    # recording that isn't actually this lesson's just by guessing a path.
    if not object_name.startswith(f"{livekit_client.room_name(lesson.id)}/"):
        raise HTTPException(status_code=404, detail="Recording not found")
    try:
        recordings.delete_recording(object_name)
    except RecordingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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

    lesson = await crud.update(db, lesson, data)
    return _lesson_out(lesson, user)


@router.delete("/lessons/{lesson_id}", status_code=204, response_class=Response)
async def delete_lesson(
    lesson_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    lesson = await _lesson_or_404(db, lesson_id)
    _authorize_owner(lesson.teacher_id, user)
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
    await crud.delete_series(db, series_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
