"""Chat endpoints (namespaced under /chat), backed by Postgres."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

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

from edubridge_shared.clients import require_internal
from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.security import TokenError, decode_token

from ...core.config import get_settings
from ...crud import conversation as crud
from ...db.session import SessionLocal, get_db
from ....notifications.service import dispatch_notification
from ...realtime import bus as rt_bus
from ...realtime import conversation_channel
from ..deps import get_current_user

_settings = get_settings()

router = APIRouter(prefix="/chat", tags=["chat"])


class StartConversation(BaseModel):
    peer_id: str


class InternalStartConversation(BaseModel):
    user_a: str
    user_b: str


class SendMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    # Set together: upload the file to Content's "chat" bucket via
    # POST /storage/presign-upload first, PUT the bytes there, then send the
    # resulting object URL here — chat itself never touches file bytes.
    attachment_url: str | None = Field(default=None, max_length=1024)
    attachment_name: str | None = Field(default=None, max_length=255)


def _uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid id") from exc


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@router.post("/conversations", status_code=201)
async def start_conversation(
    payload: StartConversation,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    participants = sorted([user.id, payload.peer_id])
    existing = await crud.find_by_participants(db, participants)
    if existing:
        return {"id": str(existing.id), "participants": participants}
    conv = await crud.create_conversation(db, participants)
    return {"id": str(conv.id), "participants": participants}


@router.post(
    "/conversations/internal",
    status_code=201,
    dependencies=[Depends(require_internal)],
)
async def start_conversation_internal(
    payload: InternalStartConversation,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Auto-create (or find) a conversation between two explicit users — for
    other departments to call, not end users. Used so a newly enrolled
    student can reach their teacher and platform admins without either side
    having to start the chat manually first (see academics' `add_student`).
    """
    if payload.user_a == payload.user_b:
        raise HTTPException(status_code=400, detail="user_a and user_b must differ")
    participants = sorted([payload.user_a, payload.user_b])
    existing = await crud.find_by_participants(db, participants)
    if existing:
        return {"id": str(existing.id), "participants": participants}
    conv = await crud.create_conversation(db, participants)
    return {"id": str(conv.id), "participants": participants}


@router.get("/conversations")
async def list_conversations(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    conversations = await crud.list_for_user(db, user.id)
    return [
        {
            "id": str(c.id),
            "participants": c.participants,
            "last_text": c.last_text,
            "last_message_at": c.last_message_at,
        }
        for c in conversations
    ]


async def _require_member(db: AsyncSession, cid: str, user_id: str):
    conv = await crud.get_conversation(db, _uuid(cid))
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user_id not in conv.participants:
        raise HTTPException(status_code=403, detail="Not a participant")
    return conv


@router.post("/conversations/{cid}/messages", status_code=201)
async def send_message(
    cid: str,
    payload: SendMessage,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    conv = await _require_member(db, cid, user.id)
    now = _now()
    message = await crud.add_message(
        db, conv, user.id, payload.text, now, payload.attachment_url, payload.attachment_name
    )
    # Push the new message to everyone watching this conversation live.
    await rt_bus.publish(
        conversation_channel(cid),
        {
            "id": str(message.id),
            "conversation_id": cid,
            "sender_id": user.id,
            "text": payload.text,
            "attachment_url": payload.attachment_url,
            "attachment_name": payload.attachment_name,
            "created_at": now.isoformat(),
        },
    )
    # Also notify (in-app + push) everyone else in the conversation, in case
    # they don't have this chat's WebSocket open right now — the live socket
    # above only reaches someone actively viewing this thread.
    preview = payload.text if len(payload.text) <= 200 else payload.text[:197] + "..."
    for recipient_id in conv.participants:
        if recipient_id == user.id:
            continue
        await dispatch_notification(
            db,
            background_tasks,
            user_id=recipient_id,
            type="chat_message",
            title="Новое сообщение",
            body=preview,
        )
    return {"id": str(message.id), "created_at": now}


@router.websocket("/ws/{cid}")
async def chat_ws(websocket: WebSocket, cid: str, token: str = Query(...)) -> None:
    """Live message stream for one conversation. Authenticate with ?token=."""
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
    # A plain `db: AsyncSession = Depends(get_db)` here would hold a pooled
    # connection (with an open transaction) for the entire lifetime of the
    # socket, not just this one lookup — the `async for` loop below can run
    # for as long as the browser tab is open, and Starlette has no reliable
    # way to notice a dead TCP peer while it's only ever writing, never
    # reading. A handful of open chat tabs was enough to exhaust engagement's
    # whole pool (5 + 2 overflow) and start timing out every other request in
    # the department — confirmed live via `idle in transaction` sessions
    # sitting on exactly this query in `pg_stat_activity`. Open a short-lived
    # session for just this check instead.
    async with SessionLocal() as db:
        conv = await crud.get_conversation(db, _uuid(cid))
    if conv is None or payload.sub not in conv.participants:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        async for message in rt_bus.subscribe(conversation_channel(cid)):
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass


@router.get("/conversations/{cid}/messages")
async def list_messages(
    cid: str,
    limit: int = Query(default=50, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await _require_member(db, cid, user.id)
    messages = await crud.list_messages(db, _uuid(cid), limit)
    return [
        {
            "id": str(m.id),
            "sender_id": m.sender_id,
            "text": m.text,
            "attachment_url": m.attachment_url,
            "attachment_name": m.attachment_name,
            "created_at": m.created_at,
            "read_by": m.read_by,
        }
        for m in messages
    ]


@router.post("/conversations/{cid}/read")
async def mark_read(
    cid: str, user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    await _require_member(db, cid, user.id)
    marked = await crud.mark_read(db, _uuid(cid), user.id)
    return {"marked_read": marked}
