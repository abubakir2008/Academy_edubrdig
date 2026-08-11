"""Lead endpoints (namespaced under /leads).

There is no self-registration on this platform — every account is
admin-created (see identity's `/auth/admin/users`). `POST /leads` is the only
public, unauthenticated write in this department: it's how a visitor with no
account yet actually reaches staff, from the marketing site's `/onboarding`
form. Everything else here is staff-only, for following up.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import lead as crud
from ...db.session import get_db
from ...models.lead import Lead
from ...schemas.lead import LeadCreate, LeadOut, LeadStatusUpdate
from ..deps import require_roles

router = APIRouter(prefix="/leads", tags=["leads"])
require_staff = require_roles(Role.ADMIN, Role.SUPER_ADMIN)

# Below this age, a repeat submission from the same phone/email is almost
# certainly a double-click or a resubmit-after-editing — hand back the
# existing lead instead of writing a near-identical row.
_INSTANT_DUPLICATE_WINDOW = timedelta(minutes=5)
# Beyond that but still within a day, it looks like actual repeat-submission
# spam (the same contact hitting the form over and over) — reject outright
# instead of quietly growing the table.
_SPAM_WINDOW = timedelta(hours=24)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate, response: Response, db: AsyncSession = Depends(get_db)
) -> dict:
    now = datetime.now(tz=timezone.utc)
    recent = await crud.find_recent_by_contact(
        db,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        since=now - _SPAM_WINDOW,
    )
    if recent is not None:
        if now - recent.created_at <= _INSTANT_DUPLICATE_WINDOW:
            response.status_code = status.HTTP_200_OK
            return {"id": str(recent.id), "status": recent.status}
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A request with this phone or email was already submitted recently — we'll be in touch soon.",
        )

    lead = await crud.create(db, payload.model_dump())
    return {"id": str(lead.id), "status": lead.status}


@router.get("", response_model=list[LeadOut])
async def list_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[LeadOut]:
    leads = await crud.list_all(db, status_filter)
    return [LeadOut.model_validate(lead) for lead in leads]


async def _lead_or_404(db: AsyncSession, lead_id: uuid.UUID) -> Lead:
    lead = await crud.get(db, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/{lead_id}/status", response_model=LeadOut)
async def set_lead_status(
    lead_id: uuid.UUID,
    payload: LeadStatusUpdate,
    _: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> LeadOut:
    lead = await _lead_or_404(db, lead_id)
    lead = await crud.update_status(db, lead, payload.status)
    return LeadOut.model_validate(lead)
