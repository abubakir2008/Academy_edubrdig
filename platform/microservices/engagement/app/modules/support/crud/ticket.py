"""Support ticket persistence (Postgres)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.ticket import Ticket, TicketMessage


async def create_ticket(
    db: AsyncSession,
    user_id: str,
    subject: str,
    priority: str,
    kind: str = "general",
    payment_id: uuid.UUID | None = None,
) -> Ticket:
    ticket = Ticket(
        user_id=user_id, subject=subject, priority=priority, status="open",
        kind=kind, payment_id=payment_id,
    )
    db.add(ticket)
    await db.flush()
    return ticket


async def add_message(
    db: AsyncSession, ticket_id: uuid.UUID, sender_id: str, text: str, is_staff: bool
) -> TicketMessage:
    message = TicketMessage(
        ticket_id=ticket_id, sender_id=sender_id, text=text, is_staff=is_staff
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_ticket(db: AsyncSession, ticket_id: uuid.UUID) -> Ticket | None:
    return await db.get(Ticket, ticket_id)


async def list_for_user(db: AsyncSession, user_id: str) -> list[Ticket]:
    result = await db.execute(
        select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.updated_at.desc())
    )
    return list(result.scalars().all())


async def list_all(db: AsyncSession, status: str | None) -> list[Ticket]:
    stmt = select(Ticket).order_by(Ticket.updated_at.desc())
    if status:
        stmt = stmt.where(Ticket.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_messages(db: AsyncSession, ticket_id: uuid.UUID) -> list[TicketMessage]:
    result = await db.execute(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc())
    )
    return list(result.scalars().all())


async def set_status(db: AsyncSession, ticket: Ticket, status: str) -> Ticket:
    ticket.status = status
    await db.commit()
    await db.refresh(ticket)
    return ticket
