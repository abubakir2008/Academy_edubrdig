"""Calendar department: homework — created/graded by a lesson's own teacher,
submitted by its own student, against a real academics roster (same
two-department boot as test_calendar_lessons.py).
"""

from __future__ import annotations

import uuid

import pytest

from tests.test_calendar_lessons import (
    _headers,
    _make_course_with_teacher,
    _next_monday_at,
    academics_and_calendar,
)

pytestmark = pytest.mark.asyncio


async def _make_lesson(academics_client, calendar_client, teacher_id, student_id) -> tuple[str, str]:
    super_admin = _headers("super_admin")
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
    return course_id, created.json()["id"]


async def test_teacher_can_assign_and_grade_homework(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id, student_id = str(uuid.uuid4()), str(uuid.uuid4())
    _course_id, lesson_id = await _make_lesson(academics_client, calendar_client, teacher_id, student_id)
    teacher_headers = _headers("tutor", teacher_id)

    created = await calendar_client.post(
        f"/calendar/lessons/{lesson_id}/homework",
        json={"student_id": student_id, "title": "Essay 250 words", "due_date": None},
        headers=teacher_headers,
    )
    assert created.status_code == 201, created.text
    homework = created.json()
    assert homework["status"] == "assigned"
    hw_id = homework["id"]

    graded = await calendar_client.put(
        f"/calendar/homework/{hw_id}/grade",
        json={"grade": 6.5, "comment": "Good fluency."},
        headers=teacher_headers,
    )
    assert graded.status_code == 200, graded.text
    assert graded.json()["status"] == "graded"
    assert graded.json()["grade"] == 6.5


async def test_homework_can_be_graded_immediately_at_creation(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id, student_id = str(uuid.uuid4()), str(uuid.uuid4())
    _course_id, lesson_id = await _make_lesson(academics_client, calendar_client, teacher_id, student_id)

    created = await calendar_client.post(
        f"/calendar/lessons/{lesson_id}/homework",
        json={"student_id": student_id, "title": "Essay", "grade": 7.0, "comment": "Great job"},
        headers=_headers("tutor", teacher_id),
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "graded"
    assert created.json()["grade"] == 7.0


async def test_cannot_assign_homework_to_a_student_not_enrolled(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id, student_id, outsider = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _course_id, lesson_id = await _make_lesson(academics_client, calendar_client, teacher_id, student_id)

    resp = await calendar_client.post(
        f"/calendar/lessons/{lesson_id}/homework",
        json={"student_id": outsider, "title": "Essay"},
        headers=_headers("tutor", teacher_id),
    )
    assert resp.status_code == 400, resp.text


async def test_only_the_lessons_own_teacher_can_assign_homework(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id, student_id, other_tutor = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _course_id, lesson_id = await _make_lesson(academics_client, calendar_client, teacher_id, student_id)

    resp = await calendar_client.post(
        f"/calendar/lessons/{lesson_id}/homework",
        json={"student_id": student_id, "title": "Essay"},
        headers=_headers("tutor", other_tutor),
    )
    assert resp.status_code == 403, resp.text


async def test_student_can_submit_only_their_own_homework(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id, student_id, other_student = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    _course_id, lesson_id = await _make_lesson(academics_client, calendar_client, teacher_id, student_id)

    created = await calendar_client.post(
        f"/calendar/lessons/{lesson_id}/homework",
        json={"student_id": student_id, "title": "Essay"},
        headers=_headers("tutor", teacher_id),
    )
    hw_id = created.json()["id"]

    forbidden = await calendar_client.post(
        f"/calendar/homework/{hw_id}/submit",
        json={"submission_url": "/storage/public/materials/x"},
        headers=_headers("student", other_student),
    )
    assert forbidden.status_code == 403, forbidden.text

    ok = await calendar_client.post(
        f"/calendar/homework/{hw_id}/submit",
        json={"submission_url": "/storage/public/materials/x"},
        headers=_headers("student", student_id),
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "submitted"


async def test_homework_me_scopes_by_role(academics_and_calendar):
    academics_client, calendar_client = academics_and_calendar
    teacher_id, student_id = str(uuid.uuid4()), str(uuid.uuid4())
    _course_id, lesson_id = await _make_lesson(academics_client, calendar_client, teacher_id, student_id)

    await calendar_client.post(
        f"/calendar/lessons/{lesson_id}/homework",
        json={"student_id": student_id, "title": "Essay"},
        headers=_headers("tutor", teacher_id),
    )

    as_student = await calendar_client.get("/calendar/homework/me", headers=_headers("student", student_id))
    assert as_student.status_code == 200
    assert len(as_student.json()) == 1

    as_teacher = await calendar_client.get("/calendar/homework/me", headers=_headers("tutor", teacher_id))
    assert as_teacher.status_code == 200
    assert len(as_teacher.json()) == 1

    as_other_student = await calendar_client.get(
        "/calendar/homework/me", headers=_headers("student", str(uuid.uuid4()))
    )
    assert as_other_student.status_code == 200
    assert as_other_student.json() == []
