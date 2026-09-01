"""Backoffice department: analytics event ingestion trusts only the
caller's own identity.

`POST /analytics/events` used to take `user_id` straight from the request
body — any authenticated account could log events (and so skew the
revenue/DAU figures `GET /analytics/metrics/summary` reports to admins)
under any user_id it liked. Two different callers sending the *same*
spoofed user_id in the body should still count as two distinct users once
that's ignored server-side.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from tests.conftest import mint_access_token

pytestmark = pytest.mark.asyncio


def _headers(role: str, user_id: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_access_token(user_id or str(uuid.uuid4()), role)}"}


@pytest.mark.parametrize("department_app", ["backoffice"], indirect=True)
async def test_event_user_id_comes_from_the_token_not_the_body(department_app):
    _main, client = department_app
    spoofed_id = str(uuid.uuid4())

    for _ in range(2):
        resp = await client.post(
            "/analytics/events",
            json={"event_type": "login", "user_id": spoofed_id},
            headers=_headers("student"),
        )
        assert resp.status_code == 201, resp.text

    today = date.today()
    summary = await client.get(
        "/analytics/metrics/summary",
        params={
            "date_from": (today - timedelta(days=1)).isoformat(),
            "date_to": (today + timedelta(days=1)).isoformat(),
        },
        headers=_headers("super_admin"),
    )
    assert summary.status_code == 200, summary.text
    # Two different real callers, both trying to log in under the same
    # spoofed id -- if the spoof had been honored this would be 1.
    assert summary.json()["unique_users"] == 2
