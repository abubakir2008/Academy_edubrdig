"""Calendar department: lesson scheduling against a real academics department,
plus joining a lesson's LiveKit room.

``academics_client.py`` (calendar's ServiceClient call into academics'
``/courses/...``) is the platform's first real cross-department synchronous
call. These tests boot BOTH departments in one process — academics for real
(its own throwaway schema, real routing/role-checks) and calendar wired to
reach it through an in-process ASGI transport (see the ``academics_and_calendar``
fixture) — so the authorization hand-off is actually exercised, not mocked.
Only the TCP hop is skipped; nothing about either department's own logic is.

Unlike the old Zoom integration (which needed live fakes for its three
outbound HTTP calls — there's no real Zoom sandbox in CI), a LiveKit join
token is a self-signed JWT minted entirely in-process (see
``services/livekit_client.py``), so the join tests below mint and verify a
*real* token against the test secret in ``conftest.py`` — nothing to stub.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt as pyjwt
import pytest
import pytest_asyncio

from tests.conftest import _boot_department, _drop_department, mint_access_token

pytestmark = pytest.mark.asyncio

_LIVEKIT_API_SECRET = "test-secret-32-bytes-long-enough!!"


def _token(role: str, user_id: str | None = None) -> str:
    return mint_access_token(user_id or str(uuid.uuid4()), role)


def _headers(role: str, user_id: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(role, user_id)}"}


def _next_monday_at(hour: int) -> datetime:
    now = datetime.now(tz=timezone.utc)
    days_ahead = (0 - now.weekday()) % 7
    days_ahead = days_ahead if days_ahead > 0 else 7  # never today
    return (now + timedelta(days=days_ahead)).replace(hour=hour, minute=0, second=0, microsecond=0)


@pytest_asyncio.fixture
async def academics_and_calendar():
    academics_main, academics_engine, academics_schema = await _boot_department("academics")
    calendar_main, calendar_engine, calendar_schema = await _boot_department("calendar")

    # Point calendar's ServiceClient at academics' real app in-process —
    # no mock, no real socket, just no TCP hop.
    from app.modules.calendar.services import academics_client as ac

    ac._academics._client = httpx.AsyncClient(transport=httpx.ASGITransport(app=academics_main.app))

    async with (
        httpx.AsyncClient(transport=httpx.ASGITransport(app=academics_main.app), base_url="http://test") as a_client,
        httpx.AsyncClient(transport=httpx.ASGITransport(app=calendar_main.app), base_url="http://test") as c_client,
    ):
        yield a_client, c_client

    await ac._academics.aclose()
    await _drop_department(academics_engine, academics_schema)
    await _drop_department(calendar_engine, calendar_schema)


async def _make_course_with_teacher(academics_client: httpx.AsyncClient, teacher_id: str) -> str:
    super_admin = _headers("super_admin")
    created = await academics_client.post("/courses", json={"title": "Course"}, headers=super_admin)
    course_id = created.json()["id"]
    resp = await academics_client.put(
        f"/courses/{course_id}/teacher", json={"teacher_id": teacher_id}, headers=super_admin
    )
    assert resp.status_code == 200, resp.text
    return course_id


async def test_tutor_can_schedule_lesson_in_own_course(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)

    resp = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": _next_monday_at(10).isoformat(), "duration_minutes": 60},
        headers=_headers("tutor", teacher_id),
    )
    assert resp.status_code == 201, resp.text
    lesson = resp.json()
    assert lesson["teacher_id"] == teacher_id
    assert lesson["course_id"] == course_id


async def test_tutor_cannot_schedule_in_someone_elses_course(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    real_teacher = str(uuid.uuid4())
    other_tutor = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, real_teacher)

    resp = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": _next_monday_at(10).isoformat(), "duration_minutes": 60},
        headers=_headers("tutor", other_tutor),
    )
    assert resp.status_code == 403, resp.text


async def test_scheduling_into_unknown_course_is_404(academics_and_calendar):
    _academics_client, calendar_client = academics_and_calendar
    resp = await calendar_client.post(
        "/calendar/lessons",
        json={
            "course_id": str(uuid.uuid4()),
            "scheduled_start": _next_monday_at(10).isoformat(),
            "duration_minutes": 60,
        },
        headers=_headers("tutor", str(uuid.uuid4())),
    )
    assert resp.status_code == 404


async def test_double_booking_the_same_slot_conflicts(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    headers = _headers("tutor", teacher_id)
    start = _next_monday_at(10).isoformat()

    first = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": start, "duration_minutes": 60},
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": start, "duration_minutes": 30},
        headers=headers,
    )
    assert second.status_code == 409, second.text


async def test_student_sees_lessons_of_enrolled_course(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    super_admin = _headers("super_admin")
    teacher_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    enrolled = await academics_client.post(
        f"/courses/{course_id}/students", json={"student_id": student_id}, headers=super_admin
    )
    assert enrolled.status_code == 201, enrolled.text

    created = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": _next_monday_at(10).isoformat(), "duration_minutes": 60},
        headers=_headers("tutor", teacher_id),
    )
    assert created.status_code == 201, created.text

    mine = await calendar_client.get("/calendar/lessons/me", headers=_headers("student", student_id))
    assert mine.status_code == 200, mine.text
    lessons = mine.json()
    assert len(lessons) == 1

    ics = await calendar_client.get(f"/calendar/lessons/me.ics?token={_token('student', student_id)}")
    assert ics.status_code == 200
    assert "BEGIN:VEVENT" in ics.text


async def test_join_lesson_mints_a_real_livekit_token_for_teacher_and_student(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    super_admin = _headers("super_admin")
    teacher_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    enrolled = await academics_client.post(
        f"/courses/{course_id}/students", json={"student_id": student_id}, headers=super_admin
    )
    assert enrolled.status_code == 201, enrolled.text

    created = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": _next_monday_at(10).isoformat(), "duration_minutes": 60},
        headers=_headers("tutor", teacher_id),
    )
    assert created.status_code == 201, created.text
    lesson_id = created.json()["id"]

    for role, user_id in [("tutor", teacher_id), ("student", student_id)]:
        resp = await calendar_client.get(
            f"/calendar/lessons/{lesson_id}/join?name=Test%20User", headers=_headers(role, user_id)
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["livekit_url"] == "wss://test.livekit.cloud"
        assert body["room"] == f"lesson-{lesson_id}"
        # Not a mock — a real LiveKit access token, verified against the
        # same secret the calendar department was configured with.
        claims = pyjwt.decode(body["token"], _LIVEKIT_API_SECRET, algorithms=["HS256"])
        assert claims["sub"] == user_id
        assert claims["name"] == "Test User"
        assert claims["video"]["room"] == f"lesson-{lesson_id}"
        assert claims["video"]["roomJoin"] is True


async def test_join_lesson_rejects_a_tutor_who_is_not_the_teacher(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    other_tutor = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)

    created = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": _next_monday_at(10).isoformat(), "duration_minutes": 60},
        headers=_headers("tutor", teacher_id),
    )
    lesson_id = created.json()["id"]

    resp = await calendar_client.get(f"/calendar/lessons/{lesson_id}/join", headers=_headers("tutor", other_tutor))
    assert resp.status_code == 403, resp.text


async def test_individual_lesson_is_only_visible_to_its_own_student(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    super_admin = _headers("super_admin")
    teacher_id = str(uuid.uuid4())
    target_student = str(uuid.uuid4())
    other_student = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    for sid in (target_student, other_student):
        enrolled = await academics_client.post(
            f"/courses/{course_id}/students", json={"student_id": sid}, headers=super_admin
        )
        assert enrolled.status_code == 201, enrolled.text

    created = await calendar_client.post(
        "/calendar/lessons",
        json={
            "course_id": course_id,
            "scheduled_start": _next_monday_at(10).isoformat(),
            "duration_minutes": 60,
            "student_id": target_student,
        },
        headers=_headers("tutor", teacher_id),
    )
    assert created.status_code == 201, created.text
    lesson_id = created.json()["id"]
    assert created.json()["student_id"] == target_student

    mine = await calendar_client.get("/calendar/lessons/me", headers=_headers("student", target_student))
    assert len(mine.json()) == 1

    not_mine = await calendar_client.get("/calendar/lessons/me", headers=_headers("student", other_student))
    assert not_mine.json() == []

    forbidden = await calendar_client.get(
        f"/calendar/lessons/{lesson_id}", headers=_headers("student", other_student)
    )
    assert forbidden.status_code == 403, forbidden.text


async def test_individual_lesson_rejects_a_student_not_enrolled_in_the_course(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    outsider_student = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)

    resp = await calendar_client.post(
        "/calendar/lessons",
        json={
            "course_id": course_id,
            "scheduled_start": _next_monday_at(10).isoformat(),
            "duration_minutes": 60,
            "student_id": outsider_student,
        },
        headers=_headers("tutor", teacher_id),
    )
    assert resp.status_code == 400, resp.text


async def test_join_lesson_rejects_a_student_not_enrolled_in_the_course(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    outsider_student = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)

    created = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": _next_monday_at(10).isoformat(), "duration_minutes": 60},
        headers=_headers("tutor", teacher_id),
    )
    lesson_id = created.json()["id"]

    resp = await calendar_client.get(
        f"/calendar/lessons/{lesson_id}/join", headers=_headers("student", outsider_student)
    )
    assert resp.status_code == 403, resp.text
