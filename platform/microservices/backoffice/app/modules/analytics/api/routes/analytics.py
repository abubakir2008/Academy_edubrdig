"""Analytics endpoints (namespaced under /analytics)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...db.session import get_db
from ...models.event import EventLog
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/analytics", tags=["analytics"])
require_admin = require_roles(Role.ADMIN, Role.SUPER_ADMIN)


class EventIn(BaseModel):
    event_type: str = Field(max_length=64)
    value_cents: int | None = None
    payload: dict = Field(default_factory=dict)


@router.post("/events", status_code=201)
async def ingest_event(
    payload: EventIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # user_id always comes from the caller's own token, never the request
    # body — otherwise anyone could log events (and the revenue/DAU figures
    # they feed on the admin dashboard) under any user_id they like.
    event = EventLog(user_id=uuid.UUID(user.id), **payload.model_dump())
    db.add(event)
    await db.commit()
    return {"status": "recorded"}


def _bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time.min, tzinfo=timezone.utc)
    end = datetime.combine(d, time.max, tzinfo=timezone.utc)
    return start, end


@router.get("/metrics/summary")
async def summary(
    date_from: date = Query(...),
    date_to: date = Query(...),
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    start, _s = _bounds(date_from)
    _e, end = _bounds(date_to)
    result = await db.execute(
        select(
            func.count(EventLog.id),
            func.count(func.distinct(EventLog.user_id)),
            func.coalesce(func.sum(EventLog.value_cents), 0),
        ).where(EventLog.occurred_at >= start, EventLog.occurred_at <= end)
    )
    total, unique_users, revenue = result.one()
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total_events": int(total),
        "unique_users": int(unique_users),
        "revenue_cents": int(revenue),
    }


@router.get("/metrics/dau")
async def dau(
    day: date = Query(default_factory=lambda: datetime.now(tz=timezone.utc).date()),
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    start, end = _bounds(day)
    result = await db.execute(
        select(func.count(func.distinct(EventLog.user_id))).where(
            EventLog.occurred_at >= start, EventLog.occurred_at <= end
        )
    )
    return {"date": day.isoformat(), "dau": int(result.scalar_one())}


@router.get("/metrics/top-events")
async def top_events(
    limit: int = Query(default=10, le=50),
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(EventLog.event_type, func.count(EventLog.id).label("cnt"))
        .group_by(EventLog.event_type)
        .order_by(func.count(EventLog.id).desc())
        .limit(limit)
    )
    return [{"event_type": et, "count": int(c)} for et, c in result.all()]
