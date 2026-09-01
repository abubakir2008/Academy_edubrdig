"""Shared notification dispatch — the one place that writes a Notification
row, pushes it to a live WebSocket, and (for channel="push") fans it out to
every device the recipient has registered. Used both by the public
`POST /notifications` endpoint and directly by sibling modules in this same
department (chat, in-process — no HTTP round trip needed since they share
this app and this department's schema) that need to notify a user about
something that just happened.
"""

from __future__ import annotations

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from .crud import notification as notification_crud
from .crud import preference as preference_crud
from .crud import push_token as push_token_crud
from .push import send_push
from .realtime import bus as rt_bus
from .realtime import user_channel

#: Only these `type`s are gated by a preference — anything else (e.g. a
#: staff-sent POST /notifications with some other type) always pushes, since
#: there's no matching toggle for the recipient to have turned off.
_PREFERENCE_BY_TYPE = {
    "lesson_reminder": "lesson_reminders",
    "chat_message": "chat_messages",
    "homework_assigned": "homework",
    "homework_graded": "homework",
}


async def dispatch_notification(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    user_id: str,
    type: str,
    title: str,
    body: str | None,
    channel: str = "push",
) -> str:
    """Creates the notification, publishes it to any live WebSocket, and —
    for channel="push" — schedules a push send after the response goes out,
    unless the recipient has turned that category of push off. Preferences
    only gate push; the row and the WebSocket publish above still always
    happen, so the in-app list is never missing something the user just
    can't see reflected on their lock screen. Returns the new notification's
    id."""
    notification = await notification_crud.create(
        db, {"user_id": user_id, "type": type, "title": title, "body": body, "channel": channel}
    )
    await rt_bus.publish(
        user_channel(user_id),
        {"id": str(notification.id), "type": type, "title": title, "body": body},
    )
    if channel == "push":
        pref_field = _PREFERENCE_BY_TYPE.get(type)
        allowed = True
        if pref_field is not None:
            pref = await preference_crud.get_or_create(db, user_id)
            allowed = getattr(pref, pref_field)
        if allowed:
            device_tokens = await push_token_crud.tokens_for_user(db, user_id)
            background_tasks.add_task(send_push, device_tokens, title, body)
    return str(notification.id)
