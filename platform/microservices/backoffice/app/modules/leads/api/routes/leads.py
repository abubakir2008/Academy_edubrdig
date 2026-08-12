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
from ..deps import get_current_user, require_roles

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


@router.get("/me", response_model=list[LeadOut])
async def list_my_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LeadOut]:
    """Leads left on this tutor's own public profile ("Оставить заявку") —
    so a tutor can see who asked for them by name without needing staff
    access to the full /leads list. 403s for anyone who isn't a tutor;
    registered before /{lead_id}/status so the literal path "me" can't be
    swallowed by a future GET /{lead_id} route."""
    if user.role != Role.TUTOR.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a tutor")
    leads = await crud.list_for_tutor(db, uuid.UUID(user.id), status_filter)
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
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LeadOut:
    lead = await _lead_or_404(db, lead_id)
    is_staff = user.role in (Role.ADMIN.value, Role.SUPER_ADMIN.value)
    owns_lead = user.role == Role.TUTOR.value and lead.preferred_tutor_id == uuid.UUID(user.id)
    if not (is_staff or owns_lead):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    lead = await crud.update_status(db, lead, payload.status)
    return LeadOut.model_validate(lead)
