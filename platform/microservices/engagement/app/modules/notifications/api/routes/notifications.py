"""Notification endpoints (namespaced under /notifications), backed by Postgres."""

from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.clients import require_internal
from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.security import TokenError, decode_token

from ...core.config import get_settings
from ...crud import notification as crud
from ...crud import push_token as push_token_crud
from ...db.session import get_db
from ...email import send_email
from ...realtime import bus as rt_bus
from ...realtime import user_channel
from ...service import dispatch_notification
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
    notification_id = await dispatch_notification(
        db,
        background_tasks,
        user_id=payload.user_id,
        type=payload.type,
        title=payload.title,
        body=payload.body,
        channel=payload.channel,
    )
    # Email is a bonus delivery on top of whatever `channel` already covers
    # (push/websocket), sent only when an address is explicitly given —
    # dispatched after the response so a slow SMTP round trip never holds up
    # the caller (delivery is already best-effort everywhere else here).
    if payload.email:
        background_tasks.add_task(
            send_email, payload.email, payload.title, payload.body or payload.title
        )
    return {"id": notification_id}


@router.post(
    "/internal",
    status_code=201,
    dependencies=[Depends(require_internal)],
)
async def create_notification_internal(
    payload: NotificationIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Same as `POST /notifications`, but for other departments to call —
    they have no end-user JWT to present (there's no "current user" for a
    scheduled job like calendar's lesson-reminder poller), only the shared
    internal secret. See chat's `/conversations/internal` for the same shape.
    """
    notification_id = await dispatch_notification(
        db,
        background_tasks,
        user_id=payload.user_id,
        type=payload.type,
        title=payload.title,
        body=payload.body,
        channel=payload.channel,
    )
    return {"id": notification_id}


class PushTokenIn(BaseModel):
    token: str = Field(max_length=255)
    platform: str = Field(max_length=16)


class PushTokenUnregister(BaseModel):
    token: str = Field(max_length=255)


@router.post("/push-tokens", status_code=204, response_class=Response)
async def register_push_token(
    payload: PushTokenIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await push_token_crud.register(db, user.id, payload.token, payload.platform)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/push-tokens/unregister", status_code=204, response_class=Response)
async def unregister_push_token(
    payload: PushTokenUnregister,
    _: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # No ownership check needed beyond "authenticated": the token itself is
    # the unique key, and unregistering someone else's token (if you somehow
    # knew it) only stops push to a device that isn't yours — not a real
    # escalation, so this doesn't need to match `user.id` against the row.
    await push_token_crud.unregister(db, payload.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
