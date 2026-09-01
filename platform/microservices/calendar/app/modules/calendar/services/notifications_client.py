"""Notify a user from calendar's own background/internal code paths (no
end-user JWT to forward — see engagement's `POST /notifications/internal`,
guarded by the shared internal secret instead). Used by the lesson-reminder
poller and by homework create/grade.
"""

from __future__ import annotations

import logging

from edubridge_shared.clients import ServiceClient, service_url

log = logging.getLogger("calendar.notifications_client")

_notifications = ServiceClient(service_url("notifications"))


async def notify(user_id: str, *, type: str, title: str, body: str) -> None:
    try:
        await _notifications.post(
            "/internal",
            json={"user_id": user_id, "type": type, "title": title, "body": body, "channel": "push"},
        )
    except Exception as exc:
        log.warning("Failed to notify user %s (%s): %s", user_id, type, exc)
