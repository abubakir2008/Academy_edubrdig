"""Engagement department: a review must point at a real, completed lesson.

Regression test for the fix to reviews/api/routes/reviews.py — previously
``lesson_id`` was optional, and Postgres's own UniqueConstraint doesn't fire
between NULLs, so one account could leave unlimited reviews for the same
tutor simply by omitting lesson_id. lesson_id is now required and verified
against the Lessons module (a cross-department call, mocked here since the
scheduling department isn't running in this test).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from edubridge_shared.clients import ServiceError
from tests.conftest import mint_access_token

pytestmark = pytest.mark.asyncio

TUTOR_ID = uuid.uuid4()
STUDENT_ID = uuid.uuid4()
LESSON_ID = uuid.uuid4()


def _lesson(status: str = "completed", tutor_id=TUTOR_ID, student_id=STUDENT_ID) -> dict:
    return {
        "id": str(LESSON_ID),
        "status": status,
        "tutor_id": str(tutor_id),
        "student_id": str(student_id),
    }


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_review_requires_a_completed_lesson(department_app, monkeypatch):
    main, client = department_app
    from app.modules.reviews.api.routes import reviews as review_routes

    monkeypatch.setattr(
        review_routes._lessons, "get", AsyncMock(return_value=_lesson(status="scheduled"))
    )
    token = mint_access_token(str(STUDENT_ID), "student")

    resp = await client.post(
        "/reviews",
        json={"tutor_id": str(TUTOR_ID), "lesson_id": str(LESSON_ID), "rating": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text
    assert "not completed" in resp.json()["detail"]


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_review_requires_lesson_to_match_tutor_and_student(department_app, monkeypatch):
    main, client = department_app
    from app.modules.reviews.api.routes import reviews as review_routes

    someone_elses_lesson = _lesson(status="completed", tutor_id=uuid.uuid4())
    monkeypatch.setattr(
        review_routes._lessons, "get", AsyncMock(return_value=someone_elses_lesson)
    )
    token = mint_access_token(str(STUDENT_ID), "student")

    resp = await client.post(
        "/reviews",
        json={"tutor_id": str(TUTOR_ID), "lesson_id": str(LESSON_ID), "rating": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text
    assert "does not match" in resp.json()["detail"]


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_a_second_review_for_the_same_lesson_is_rejected(department_app, monkeypatch):
    """This is the actual manipulation the missing constraint used to allow:
    with lesson_id required and unique per (author, lesson), the same lesson
    cannot be reviewed twice — unlike the old nullable-lesson_id path, which
    let a single account leave unlimited reviews by never sending lesson_id.
    """
    main, client = department_app
    from app.modules.reviews.api.routes import reviews as review_routes

    monkeypatch.setattr(review_routes._lessons, "get", AsyncMock(return_value=_lesson()))
    token = mint_access_token(str(STUDENT_ID), "student")
    payload = {"tutor_id": str(TUTOR_ID), "lesson_id": str(LESSON_ID), "rating": 5}

    first = await client.post("/reviews", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == 201, first.text

    second = await client.post("/reviews", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert second.status_code == 409, second.text
    assert "already reviewed" in second.json()["detail"]


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_review_rejected_when_lesson_lookup_fails(department_app, monkeypatch):
    main, client = department_app
    from app.modules.reviews.api.routes import reviews as review_routes

    monkeypatch.setattr(
        review_routes._lessons, "get", AsyncMock(side_effect=ServiceError(404, "not found"))
    )
    token = mint_access_token(str(STUDENT_ID), "student")

    resp = await client.post(
        "/reviews",
        json={"tutor_id": str(TUTOR_ID), "lesson_id": str(uuid.uuid4()), "rating": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
