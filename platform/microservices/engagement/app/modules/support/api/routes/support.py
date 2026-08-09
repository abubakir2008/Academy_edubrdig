"""Support ticket endpoints (namespaced under /support), backed by Postgres."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import ticket as crud
from ...db.session import get_db
from ...models.ticket import Ticket
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/support", tags=["support"])
require_support = require_roles(Role.ADMIN, Role.SUPER_ADMIN)

_STAFF_ROLES = {Role.ADMIN.value, Role.SUPER_ADMIN.value}


class TicketCreate(BaseModel):
    subject: str = Field(max_length=255)
    message: str = Field(min_length=1)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")


class MessageIn(BaseModel):
    text: str = Field(min_length=1)


def _serialize(t: Ticket) -> dict:
    return {
        "id": str(t.id),
        "user_id": t.user_id,
        "subject": t.subject,
        "status": t.status,
        "priority": t.priority,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.post("/tickets", status_code=201)
async def create_ticket(
    payload: TicketCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ticket = await crud.create_ticket(db, user.id, payload.subject, payload.priority)
    await crud.add_message(db, ticket.id, user.id, payload.message, is_staff=False)
    return {"id": str(ticket.id), "status": "open"}


@router.get("/tickets/me")
async def my_tickets(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    return [_serialize(t) for t in await crud.list_for_user(db, user.id)]


@router.get("/tickets")
async def all_tickets(
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(require_support),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return [_serialize(t) for t in await crud.list_all(db, status_filter)]


async def _get_ticket_for(db: AsyncSession, ticket_id: uuid.UUID, user: CurrentUser) -> Ticket:
    ticket = await crud.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.user_id != user.id and user.role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Not allowed")
    return ticket


@router.get("/tickets/{ticket_id}/messages")
async def ticket_messages(
    ticket_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await _get_ticket_for(db, ticket_id, user)
    messages = await crud.list_messages(db, ticket_id)
    return [
        {
            "id": str(m.id),
            "sender_id": m.sender_id,
            "text": m.text,
            "is_staff": m.is_staff,
            "created_at": m.created_at,
        }
        for m in messages
    ]


@router.post("/tickets/{ticket_id}/messages", status_code=201)
async def reply_ticket(
    ticket_id: uuid.UUID,
    payload: MessageIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ticket = await _get_ticket_for(db, ticket_id, user)
    is_staff = user.role in _STAFF_ROLES
    await crud.add_message(db, ticket.id, user.id, payload.text, is_staff)
    await crud.set_status(db, ticket, "pending" if is_staff else "open")
    return {"status": "sent"}


@router.post("/tickets/{ticket_id}/close")
async def close_ticket(
    ticket_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ticket = await _get_ticket_for(db, ticket_id, user)
    await crud.set_status(db, ticket, "closed")
    return {"status": "closed"}
