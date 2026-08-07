"""Support ticket endpoints (namespaced under /support), backed by Postgres."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.clients import ServiceClient, ServiceError, service_url
from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import ticket as crud
from ...db.session import get_db
from ...models.ticket import Ticket
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/support", tags=["support"])
require_support = require_roles(Role.SUPPORT_MANAGER, Role.ADMIN, Role.SUPER_ADMIN)
_finance = ServiceClient(service_url("payments"))

_STAFF_ROLES = {Role.SUPPORT_MANAGER.value, Role.ADMIN.value, Role.SUPER_ADMIN.value}


class TicketCreate(BaseModel):
    subject: str = Field(max_length=255)
    message: str = Field(min_length=1)
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    kind: str = Field(default="general", pattern="^(general|dispute)$")
    # Required when kind="dispute" — the payment this dispute is about, so
    # staff can resolve it with a real refund instead of just a note.
    payment_id: uuid.UUID | None = None


class MessageIn(BaseModel):
    text: str = Field(min_length=1)


class DisputeResolve(BaseModel):
    refund: bool
    amount_cents: int | None = Field(default=None, gt=0, description="defaults to full remaining")
    note: str | None = Field(default=None, max_length=500)


def _serialize(t: Ticket) -> dict:
    return {
        "id": str(t.id),
        "user_id": t.user_id,
        "subject": t.subject,
        "status": t.status,
        "priority": t.priority,
        "kind": t.kind,
        "payment_id": str(t.payment_id) if t.payment_id else None,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.post("/tickets", status_code=201)
async def create_ticket(
    payload: TicketCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if payload.kind == "dispute" and payload.payment_id is None:
        raise HTTPException(status_code=400, detail="A dispute needs a payment_id")
    ticket = await crud.create_ticket(
        db, user.id, payload.subject, payload.priority, payload.kind, payload.payment_id
    )
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


@router.post("/tickets/{ticket_id}/resolve")
async def resolve_dispute(
    ticket_id: uuid.UUID,
    payload: DisputeResolve,
    request: Request,
    user: CurrentUser = Depends(require_support),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Staff-only. Closes a dispute ticket, optionally issuing the refund it
    was opened about — forwards the staff member's own token to Finance,
    which already allows staff roles to refund (see payments.refund_payment)."""
    ticket = await crud.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.kind != "dispute" or ticket.payment_id is None:
        raise HTTPException(status_code=400, detail="Not a dispute ticket")

    if payload.refund:
        token = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        try:
            await _finance.post(
                f"/payments/{ticket.payment_id}/refund",
                {"amount_cents": payload.amount_cents, "reason": payload.note or "Dispute resolved"},
                token=token,
            )
        except ServiceError as exc:
            raise HTTPException(status_code=exc.status, detail=exc.detail) from exc

    await crud.add_message(
        db, ticket.id, user.id,
        payload.note or ("Refund issued." if payload.refund else "Dispute dismissed."),
        is_staff=True,
    )
    await crud.set_status(db, ticket, "closed")
    return {"status": "closed", "refunded": payload.refund}
