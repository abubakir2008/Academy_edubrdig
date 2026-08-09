"""Academics department: course CRUD and its role boundaries.

Full CRUD (create/update/delete/assign-teacher/manage-roster) is
super_admin-only; admin can list/read but never mutates; tutor and student
only ever see their own courses via /courses/me and /courses/{id}.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import mint_access_token

pytestmark = pytest.mark.asyncio


def _headers(role: str, user_id: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_access_token(user_id or str(uuid.uuid4()), role)}"}


@pytest.mark.parametrize("department_app", ["academics"], indirect=True)
async def test_super_admin_full_crud_roundtrip(department_app):
    _main, client = department_app
    admin = _headers("super_admin")
    teacher_id = str(uuid.uuid4())
    student_id = str(uuid.uuid4())

    created = await client.post("/courses", json={"title": "English B1", "description": "..."}, headers=admin)
    assert created.status_code == 201, created.text
    course_id = created.json()["id"]

    assigned = await client.put(f"/courses/{course_id}/teacher", json={"teacher_id": teacher_id}, headers=admin)
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["teacher_id"] == teacher_id

    enrolled = await client.post(f"/courses/{course_id}/students", json={"student_id": student_id}, headers=admin)
    assert enrolled.status_code == 201, enrolled.text
    assert student_id in enrolled.json()["student_ids"]

    updated = await client.put(f"/courses/{course_id}", json={"title": "English B1 (updated)"}, headers=admin)
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "English B1 (updated)"

    removed = await client.delete(f"/courses/{course_id}/students/{student_id}", headers=admin)
    assert removed.status_code == 200, removed.text
    assert student_id not in removed.json()["student_ids"]

    deleted = await client.delete(f"/courses/{course_id}", headers=admin)
    assert deleted.status_code == 204, deleted.text

    gone = await client.get(f"/courses/{course_id}", headers=admin)
    assert gone.status_code == 404


@pytest.mark.parametrize("department_app", ["academics"], indirect=True)
async def test_admin_can_view_but_not_mutate(department_app):
    _main, client = department_app
    super_admin = _headers("super_admin")
    admin = _headers("admin")

    created = await client.post("/courses", json={"title": "Math", "description": None}, headers=super_admin)
    course_id = created.json()["id"]

    listed = await client.get("/courses", headers=admin)
    assert listed.status_code == 200
    assert any(c["id"] == course_id for c in listed.json())

    read = await client.get(f"/courses/{course_id}", headers=admin)
    assert read.status_code == 200

    for resp in (
        await client.post("/courses", json={"title": "X"}, headers=admin),
        await client.put(f"/courses/{course_id}", json={"title": "X"}, headers=admin),
        await client.delete(f"/courses/{course_id}", headers=admin),
        await client.put(f"/courses/{course_id}/teacher", json={"teacher_id": str(uuid.uuid4())}, headers=admin),
    ):
        assert resp.status_code == 403, resp.text


@pytest.mark.parametrize("department_app", ["academics"], indirect=True)
async def test_tutor_sees_only_own_courses(department_app):
    _main, client = department_app
    super_admin = _headers("super_admin")
    teacher_id = str(uuid.uuid4())
    tutor = _headers("tutor", teacher_id)

    mine = await client.post("/courses", json={"title": "Mine"}, headers=super_admin)
    mine_id = mine.json()["id"]
    await client.put(f"/courses/{mine_id}/teacher", json={"teacher_id": teacher_id}, headers=super_admin)

    other = await client.post("/courses", json={"title": "Not mine"}, headers=super_admin)
    other_id = other.json()["id"]

    my_courses = await client.get("/courses/me", headers=tutor)
    assert my_courses.status_code == 200
    ids = {c["id"] for c in my_courses.json()}
    assert ids == {mine_id}

    allowed = await client.get(f"/courses/{mine_id}", headers=tutor)
    assert allowed.status_code == 200

    forbidden = await client.get(f"/courses/{other_id}", headers=tutor)
    assert forbidden.status_code == 403


@pytest.mark.parametrize("department_app", ["academics"], indirect=True)
async def test_student_sees_only_enrolled_courses(department_app):
    _main, client = department_app
    super_admin = _headers("super_admin")
    student_id = str(uuid.uuid4())
    student = _headers("student", student_id)

    enrolled_course = await client.post("/courses", json={"title": "Enrolled"}, headers=super_admin)
    enrolled_id = enrolled_course.json()["id"]
    await client.post(f"/courses/{enrolled_id}/students", json={"student_id": student_id}, headers=super_admin)

    other_course = await client.post("/courses", json={"title": "Not enrolled"}, headers=super_admin)
    other_id = other_course.json()["id"]

    my_courses = await client.get("/courses/me", headers=student)
    assert {c["id"] for c in my_courses.json()} == {enrolled_id}

    assert (await client.get(f"/courses/{enrolled_id}", headers=student)).status_code == 200
    assert (await client.get(f"/courses/{other_id}", headers=student)).status_code == 403


@pytest.mark.parametrize("department_app", ["academics"], indirect=True)
async def test_duplicate_enrollment_is_rejected(department_app):
    _main, client = department_app
    super_admin = _headers("super_admin")
    student_id = str(uuid.uuid4())

    course = await client.post("/courses", json={"title": "Course"}, headers=super_admin)
    course_id = course.json()["id"]

    first = await client.post(f"/courses/{course_id}/students", json={"student_id": student_id}, headers=super_admin)
    assert first.status_code == 201

    second = await client.post(f"/courses/{course_id}/students", json={"student_id": student_id}, headers=super_admin)
    assert second.status_code == 409
