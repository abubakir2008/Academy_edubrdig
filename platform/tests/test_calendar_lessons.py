"""Calendar department: lesson scheduling against a real academics department,
plus the Zoom integration's account-linking and hard-fail-on-unlinked policy.

``academics_client.py`` (calendar's ServiceClient call into academics'
``/courses/...``) is the platform's first real cross-department synchronous
call. These tests boot BOTH departments in one process — academics for real
(its own throwaway schema, real routing/role-checks) and calendar wired to
reach it through an in-process ASGI transport (see the ``academics_and_calendar``
fixture) — so the authorization hand-off is actually exercised, not mocked.
Only the TCP hop is skipped; nothing about either department's own logic is.

The one deliberate exception is Zoom itself: there's no real Zoom account
available in CI, so ``services.zoom_client``'s three network calls
(create/update/delete meeting, token refresh) are replaced with fakes here.
That's a stub of a thin outbound HTTP client to a third-party API, not of
this platform's own business logic or database — the conflict-detection,
recurrence, ownership and Zoom-account-required checks under test all still
run for real against a real Postgres.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio

from tests.conftest import _boot_department, _drop_department, mint_access_token

pytestmark = pytest.mark.asyncio


def _token(role: str, user_id: str | None = None) -> str:
    return mint_access_token(user_id or str(uuid.uuid4()), role)


def _headers(role: str, user_id: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(role, user_id)}"}


def _next_monday_at(hour: int) -> datetime:
    now = datetime.now(tz=timezone.utc)
    days_ahead = (0 - now.weekday()) % 7
    days_ahead = days_ahead if days_ahead > 0 else 7  # never today
    return (now + timedelta(days=days_ahead)).replace(hour=hour, minute=0, second=0, microsecond=0)


async def _fake_create_meeting(access_token, *, topic, start, duration_minutes):
    meeting_id = f"fake-{uuid.uuid4().hex[:10]}"
    return {
        "id": meeting_id,
        "join_url": f"https://zoom.example/j/{meeting_id}",
        "start_url": f"https://zoom.example/s/{meeting_id}",
    }


async def _fake_update_meeting(access_token, meeting_id, *, start, duration_minutes):
    return None


async def _fake_delete_meeting(access_token, meeting_id):
    return None


async def _fake_ensure_fresh_token(db, account):
    return "fake-access-token"


@pytest_asyncio.fixture
async def academics_and_calendar():
    academics_main, academics_engine, academics_schema = await _boot_department("academics")
    calendar_main, calendar_engine, calendar_schema = await _boot_department("calendar")

    # Point calendar's ServiceClient at academics' real app in-process —
    # no mock, no real socket, just no TCP hop.
    from app.modules.calendar.services import academics_client as ac
    from app.modules.calendar.services import zoom_client as zc

    ac._academics._client = httpx.AsyncClient(transport=httpx.ASGITransport(app=academics_main.app))

    # Zoom itself has no reachable sandbox in CI — fake the three outbound
    # calls a lesson's lifecycle makes (see module docstring for why this,
    # unlike the DB, is an acceptable thing to stub).
    zc.create_meeting = _fake_create_meeting
    zc.update_meeting = _fake_update_meeting
    zc.delete_meeting = _fake_delete_meeting
    zc.ensure_fresh_token = _fake_ensure_fresh_token

    from app.db.session import SessionLocal as CalendarSessionLocal
    from app.modules.calendar.models.zoom_account import ZoomAccount

    async def connect_zoom(tutor_id: str) -> None:
        async with CalendarSessionLocal() as db:
            db.add(
                ZoomAccount(
                    tutor_id=uuid.UUID(tutor_id),
                    access_token="fake",
                    refresh_token="fake",
                    token_expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1),
                    zoom_email=f"{tutor_id[:8]}@example.com",
                )
            )
            await db.commit()

    async with (
        httpx.AsyncClient(transport=httpx.ASGITransport(app=academics_main.app), base_url="http://test") as a_client,
        httpx.AsyncClient(transport=httpx.ASGITransport(app=calendar_main.app), base_url="http://test") as c_client,
    ):
        yield a_client, c_client, connect_zoom

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


async def test_lesson_creation_without_zoom_connected_is_409(academics_and_calendar):
    academics_client, calendar_client, _connect_zoom = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)

    resp = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": _next_monday_at(10).isoformat(), "duration_minutes": 60},
        headers=_headers("tutor", teacher_id),
    )
    assert resp.status_code == 409, resp.text
    assert "zoom" in resp.text.lower()


async def test_tutor_can_schedule_lesson_in_own_course(academics_and_calendar):
    academics_client, calendar_client, connect_zoom = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    await connect_zoom(teacher_id)

    resp = await calendar_client.post(
        "/calendar/lessons",
        json={"course_id": course_id, "scheduled_start": _next_monday_at(10).isoformat(), "duration_minutes": 60},
        headers=_headers("tutor", teacher_id),
    )
    assert resp.status_code == 201, resp.text
    lessons = resp.json()
    assert len(lessons) == 1
    assert lessons[0]["teacher_id"] == teacher_id
    assert lessons[0]["course_id"] == course_id
    assert lessons[0]["series_id"] is None
    assert lessons[0]["meeting_url"]
    assert lessons[0]["start_url"]


async def test_tutor_cannot_schedule_in_someone_elses_course(academics_and_calendar):
    academics_client, calendar_client, _connect_zoom = academics_and_calendar
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
    _academics_client, calendar_client, _connect_zoom = academics_and_calendar
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
    academics_client, calendar_client, connect_zoom = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    await connect_zoom(teacher_id)
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


async def test_weekly_recurrence_creates_n_lessons_without_conflicts(academics_and_calendar):
    academics_client, calendar_client, connect_zoom = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    await connect_zoom(teacher_id)

    resp = await calendar_client.post(
        "/calendar/lessons",
        json={
            "course_id": course_id,
            "scheduled_start": _next_monday_at(10).isoformat(),
            "duration_minutes": 60,
            "recurrence": "weekly",
            "recurrence_weeks": 4,
        },
        headers=_headers("tutor", teacher_id),
    )
    assert resp.status_code == 201, resp.text
    lessons = resp.json()
    assert len(lessons) == 4
    series_ids = {lesson["series_id"] for lesson in lessons}
    assert len(series_ids) == 1
    assert None not in series_ids
    # separate conference per lesson (not one shared per series)
    assert len({lesson["meeting_url"] for lesson in lessons}) == 4

    mine = await calendar_client.get("/calendar/lessons/me", headers=_headers("tutor", teacher_id))
    assert len(mine.json()) == 4


async def test_student_sees_lessons_of_enrolled_course(academics_and_calendar):
    academics_client, calendar_client, connect_zoom = academics_and_calendar
    super_admin = _headers("super_admin")
    teacher_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    await connect_zoom(teacher_id)
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
    # a student can join but never gets the host-start link
    assert lessons[0]["meeting_url"]
    assert lessons[0]["start_url"] is None

    ics = await calendar_client.get(f"/calendar/lessons/me.ics?token={_token('student', student_id)}")
    assert ics.status_code == 200
    assert "BEGIN:VEVENT" in ics.text


async def test_series_delete_removes_all_instances(academics_and_calendar):
    academics_client, calendar_client, connect_zoom = academics_and_calendar
    teacher_id = str(uuid.uuid4())
    course_id = await _make_course_with_teacher(academics_client, teacher_id)
    await connect_zoom(teacher_id)
    headers = _headers("tutor", teacher_id)

    created = await calendar_client.post(
        "/calendar/lessons",
        json={
            "course_id": course_id,
            "scheduled_start": _next_monday_at(10).isoformat(),
            "duration_minutes": 60,
            "recurrence": "weekly",
            "recurrence_weeks": 3,
        },
        headers=headers,
    )
    series_id = created.json()[0]["series_id"]

    deleted = await calendar_client.delete(f"/calendar/series/{series_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    mine = await calendar_client.get("/calendar/lessons/me", headers=headers)
    assert mine.json() == []


async def test_zoom_state_token_round_trip(academics_and_calendar):
    _academics_client, _calendar_client, _connect_zoom = academics_and_calendar
    from app.modules.calendar.services import zoom_oauth

    tutor_id = str(uuid.uuid4())
    state = zoom_oauth.make_state(tutor_id)
    assert zoom_oauth.read_state(state) == tutor_id

    with pytest.raises(zoom_oauth.ZoomOAuthError):
        zoom_oauth.read_state("not-a-real-token")


async def test_zoom_status_and_disconnect(academics_and_calendar):
    _academics_client, calendar_client, connect_zoom = academics_and_calendar
    tutor_id = str(uuid.uuid4())
    headers = _headers("tutor", tutor_id)

    before = await calendar_client.get("/calendar/zoom/status", headers=headers)
    assert before.json() == {"connected": False, "email": None}

    await connect_zoom(tutor_id)
    after = await calendar_client.get("/calendar/zoom/status", headers=headers)
    assert after.json()["connected"] is True

    disconnected = await calendar_client.delete("/calendar/zoom", headers=headers)
    assert disconnected.status_code == 204

    gone = await calendar_client.get("/calendar/zoom/status", headers=headers)
    assert gone.json()["connected"] is False
