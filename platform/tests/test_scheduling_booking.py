"""Scheduling department: booking must respect the tutor's calendar.

Regression test for the gap flagged in the pre-merge review — Booking only
checked for overlap with other bookings, never against the tutor's actual
working hours, so a tutor with a 9-to-5 calendar could be booked at 3 a.m.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from tests.conftest import mint_access_token

pytestmark = pytest.mark.asyncio

TUTOR_ID = uuid.uuid4()
STUDENT_ID = uuid.uuid4()

# 2024-01-01 is a Monday (weekday() == 0).
MONDAY_IN_HOURS = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)  # inside 09:00-17:00
MONDAY_OUT_OF_HOURS = datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc)  # 3 a.m.


def _fake_tutor_payload() -> dict:
    return {
        "user_id": str(TUTOR_ID),
        "is_verified": True,
        "is_active": True,
        "price_cents": 2000,
        "trial_price_cents": 1000,
        "currency": "USD",
    }


@pytest.mark.parametrize("department_app", ["scheduling"], indirect=True)
async def test_booking_rejects_time_outside_tutor_calendar(department_app, monkeypatch):
    main, client = department_app

    from app.modules.booking.api.routes import bookings as booking_routes

    monkeypatch.setattr(booking_routes._tutors, "get", AsyncMock(return_value=_fake_tutor_payload()))

    tutor_token = mint_access_token(str(TUTOR_ID), "tutor")
    student_token = mint_access_token(str(STUDENT_ID), "student")

    rules = await client.put(
        "/calendar/me/rules",
        json=[{"weekday": 0, "start_time": "09:00:00", "end_time": "17:00:00"}],
        headers={"Authorization": f"Bearer {tutor_token}"},
    )
    assert rules.status_code == 200, rules.text

    in_hours = await client.post(
        "/booking",
        json={
            "tutor_id": str(TUTOR_ID),
            "scheduled_start": MONDAY_IN_HOURS.isoformat(),
            "duration_minutes": 60,
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert in_hours.status_code == 201, in_hours.text

    out_of_hours = await client.post(
        "/booking",
        json={
            "tutor_id": str(TUTOR_ID),
            "scheduled_start": MONDAY_OUT_OF_HOURS.isoformat(),
            "duration_minutes": 60,
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert out_of_hours.status_code == 409, out_of_hours.text
    assert "not available" in out_of_hours.json()["detail"]


@pytest.mark.parametrize("department_app", ["scheduling"], indirect=True)
async def test_booking_allowed_when_tutor_has_no_calendar_configured(department_app, monkeypatch):
    """A tutor who never set up availability rules is still bookable —
    calendar enforcement only engages once rules exist (see
    calendar/crud/calendar.py::is_available)."""
    main, client = department_app

    from app.modules.booking.api.routes import bookings as booking_routes

    monkeypatch.setattr(booking_routes._tutors, "get", AsyncMock(return_value=_fake_tutor_payload()))

    student_token = mint_access_token(str(STUDENT_ID), "student")
    resp = await client.post(
        "/booking",
        json={
            "tutor_id": str(TUTOR_ID),
            "scheduled_start": MONDAY_OUT_OF_HOURS.isoformat(),
            "duration_minutes": 60,
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 201, resp.text
