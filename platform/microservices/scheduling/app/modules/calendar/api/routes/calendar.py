"""Calendar endpoints (namespaced under /calendar)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import calendar as crud
from ...db.session import get_db
from ...schemas.calendar import BlockedIn, BlockedOut, RuleIn, RuleOut, Slot
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/calendar", tags=["calendar"])
require_tutor = require_roles(Role.TUTOR)


@router.put("/me/rules", response_model=list[RuleOut])
async def set_rules(
    rules: list[RuleIn],
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> list[RuleOut]:
    saved = await crud.replace_rules(db, uuid.UUID(user.id), [r.model_dump() for r in rules])
    return [RuleOut.model_validate(r) for r in saved]


@router.get("/me/rules", response_model=list[RuleOut])
async def get_rules(
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> list[RuleOut]:
    return [RuleOut.model_validate(r) for r in await crud.list_rules(db, uuid.UUID(user.id))]


@router.post("/me/blocked", response_model=BlockedOut, status_code=201)
async def add_blocked(
    payload: BlockedIn,
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> BlockedOut:
    blocked = await crud.add_blocked(db, uuid.UUID(user.id), payload.model_dump())
    return BlockedOut.model_validate(blocked)


@router.delete("/me/blocked/{blocked_id}", status_code=204, response_class=Response)
async def delete_blocked(
    blocked_id: uuid.UUID,
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> Response:
    ok = await crud.delete_blocked(db, uuid.UUID(user.id), blocked_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Blocked time not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{tutor_id}/slots", response_model=list[Slot])
async def available_slots(
    tutor_id: uuid.UUID,
    date_from: date = Query(...),
    date_to: date = Query(...),
    slot_minutes: int = Query(default=60, ge=15, le=240),
    db: AsyncSession = Depends(get_db),
) -> list[Slot]:
    if (date_to - date_from).days > 31:
        raise HTTPException(status_code=400, detail="Date range too large (max 31 days)")
    slots = await crud.generate_slots(db, tutor_id, date_from, date_to, slot_minutes)
    return [Slot(**s) for s in slots]
