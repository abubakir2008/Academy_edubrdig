"""Notification endpoints (namespaced under /notifications), backed by Postgres."""

from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.security import TokenError, decode_token

from ...core.config import get_settings
from ...crud import notification as crud
from ...db.session import get_db
from ...email import send_email
from ...realtime import bus as rt_bus
from ...realtime import user_channel
from ..deps import get_current_user

_settings = get_settings()

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationIn(BaseModel):
    user_id: str
    type: str = Field(default="system", max_length=32)
    title: str = Field(max_length=255)
    body: str | None = None
    # email | sms | telegram | push | websocket
    channel: str = Field(default="push", max_length=16)
    # When provided, the notification is also emailed to this address.
    email: str | None = None


@router.post("", status_code=201)
async def create_notification(
    payload: NotificationIn,
    background_tasks: BackgroundTasks,
    _: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    notification = await crud.create(
        db, payload.model_dump(exclude={"email"})
    )
    # Push to any live WebSocket the user has open, right now.
    await rt_bus.publish(
        user_channel(payload.user_id),
        {
            "id": str(notification.id),
            "type": notification.type,
            "title": notification.title,
            "body": notification.body,
        },
    )
    # Deliver over the requested channel(s). Email goes out when an address is
    # given — dispatched after the response is sent so a slow SMTP round trip
    # never holds up the caller (delivery is already best-effort everywhere
    # else in this codebase).
    if payload.email:
        background_tasks.add_task(
            send_email, payload.email, payload.title, payload.body or payload.title
        )
    return {"id": str(notification.id)}


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket, token: str = Query(...)) -> None:
    """Live notification stream. Authenticate with ?token=<access_token>."""
    try:
        payload = decode_token(
            token,
            secret_key=_settings.jwt_public_key,
            algorithm=_settings.jwt_algorithm,
            expected_type="access",
        )
    except TokenError:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        async for message in rt_bus.subscribe(user_channel(payload.sub)):
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass


@router.get("/me")
async def my_notifications(
    only_unread: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    items = await crud.list_for_user(db, user.id, only_unread=only_unread, limit=limit)
    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "channel": n.channel,
            "read": n.read,
            "created_at": n.created_at,
        }
        for n in items
    ]


@router.get("/me/unread-count")
async def unread_count(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    return {"unread": await crud.unread_count(db, user.id)}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not await crud.mark_read(db, notification_id, user.id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "read"}


@router.post("/read-all")
async def mark_all_read(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    return {"marked_read": await crud.mark_all_read(db, user.id)}
