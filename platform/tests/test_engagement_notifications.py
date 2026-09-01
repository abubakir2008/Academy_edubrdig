"""Engagement department: push-token registration and notification dispatch.

`PUSH_ENABLED=false` in the test environment (see conftest.py's
`_department_env`) means `send_push` never makes a real network call to
Expo's push API here — these tests only check the Postgres/WebSocket-fanout
side of dispatch_notification, the same "no real network I/O in tests" shape
already used for email (`EMAIL_ENABLED=false`).
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import TEST_INTERNAL_SECRET, mint_access_token

pytestmark = pytest.mark.asyncio


def _headers(user_id: str, role: str = "student") -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_access_token(user_id, role)}"}


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_register_and_unregister_push_token(department_app):
    _main, client = department_app
    user_id = str(uuid.uuid4())

    registered = await client.post(
        "/notifications/push-tokens",
        json={"token": f"ExponentPushToken[{uuid.uuid4().hex}]", "platform": "ios"},
        headers=_headers(user_id),
    )
    assert registered.status_code == 204, registered.text

    unregistered = await client.post(
        "/notifications/push-tokens/unregister",
        json={"token": f"ExponentPushToken[{uuid.uuid4().hex}]"},
        headers=_headers(user_id),
    )
    assert unregistered.status_code == 204, unregistered.text


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_internal_notification_shows_up_for_its_user(department_app):
    _main, client = department_app
    user_id = str(uuid.uuid4())

    created = await client.post(
        "/notifications/internal",
        json={
            "user_id": user_id,
            "type": "lesson_reminder",
            "title": "Урок скоро начнётся",
            "body": "Алгебра в 10:00",
            "channel": "push",
        },
        headers={"X-Internal-Secret": TEST_INTERNAL_SECRET},
    )
    assert created.status_code == 201, created.text

    mine = await client.get("/notifications/me", headers=_headers(user_id))
    assert mine.status_code == 200, mine.text
    titles = [n["title"] for n in mine.json()]
    assert "Урок скоро начнётся" in titles

    unread = await client.get("/notifications/me/unread-count", headers=_headers(user_id))
    assert unread.json()["unread"] >= 1


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_internal_notification_rejects_missing_secret(department_app):
    _main, client = department_app

    resp = await client.post(
        "/notifications/internal",
        json={"user_id": str(uuid.uuid4()), "title": "x", "channel": "push"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_chat_message_notifies_the_other_participant(department_app):
    _main, client = department_app
    sender_id = str(uuid.uuid4())
    recipient_id = str(uuid.uuid4())

    conv = await client.post(
        "/chat/conversations", json={"peer_id": recipient_id}, headers=_headers(sender_id)
    )
    assert conv.status_code == 201, conv.text
    cid = conv.json()["id"]

    sent = await client.post(
        f"/chat/conversations/{cid}/messages",
        json={"text": "Привет!"},
        headers=_headers(sender_id),
    )
    assert sent.status_code == 201, sent.text

    recipient_notifications = await client.get(
        "/notifications/me", headers=_headers(recipient_id)
    )
    bodies = [n["body"] for n in recipient_notifications.json()]
    assert "Привет!" in bodies

    # The sender shouldn't get notified about their own message.
    sender_notifications = await client.get("/notifications/me", headers=_headers(sender_id))
    assert all(n["type"] != "chat_message" for n in sender_notifications.json())


@pytest.mark.parametrize("department_app", ["engagement"], indirect=True)
async def test_only_staff_can_notify_an_arbitrary_user(department_app):
    """POST /notifications lets the caller pick any target user_id (and,
    with `email` set, relay mail to any address) — before this check, any
    authenticated account (student/tutor) could use it to spam another
    user_id or send email through the platform's own SMTP to anyone."""
    _main, client = department_app
    target_id = str(uuid.uuid4())

    as_student = await client.post(
        "/notifications",
        json={"user_id": target_id, "title": "hi", "channel": "push"},
        headers=_headers(str(uuid.uuid4()), role="student"),
    )
    assert as_student.status_code == 403, as_student.text

    as_admin = await client.post(
        "/notifications",
        json={"user_id": target_id, "title": "hi", "channel": "push"},
        headers=_headers(str(uuid.uuid4()), role="admin"),
    )
    assert as_admin.status_code == 201, as_admin.text
