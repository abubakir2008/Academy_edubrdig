"""Tutor profile + public browsing endpoints (namespaced under /tutors)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import tutor as crud
from ...crud.tutor import TutorFilters
from ...db.session import get_db
from ...schemas.tutor import (
    CertificateIn,
    CertificateOut,
    TutorDetail,
    TutorSummary,
    TutorUpsert,
    WorkingHourIn,
)
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/tutors", tags=["tutors"])

require_tutor = require_roles(Role.TUTOR)


# --------------------------- Self-management ---------------------------

@router.post("/me", response_model=TutorDetail, status_code=status.HTTP_201_CREATED)
async def upsert_my_tutor_profile(
    payload: TutorUpsert,
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> TutorDetail:
    tutor = await crud.get_or_create(db, uuid.UUID(user.id))
    data = payload.model_dump(exclude_unset=True)
    tutor = await crud.update(db, tutor, data)
    return TutorDetail.model_validate(tutor)


@router.get("/me", response_model=TutorDetail)
async def get_my_tutor_profile(
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> TutorDetail:
    tutor = await crud.get_or_create(db, uuid.UUID(user.id))
    return TutorDetail.model_validate(tutor)


@router.put("/me/working-hours", response_model=TutorDetail)
async def set_working_hours(
    hours: list[WorkingHourIn],
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> TutorDetail:
    tutor = await crud.get_or_create(db, uuid.UUID(user.id))
    tutor = await crud.replace_working_hours(
        db, tutor, [h.model_dump() for h in hours]
    )
    return TutorDetail.model_validate(tutor)


@router.post("/me/certificates", response_model=CertificateOut, status_code=201)
async def add_certificate(
    payload: CertificateIn,
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> CertificateOut:
    await crud.get_or_create(db, uuid.UUID(user.id))
    cert = await crud.add_certificate(db, uuid.UUID(user.id), payload.model_dump())
    return CertificateOut.model_validate(cert)


@router.delete(
    "/me/certificates/{cert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_certificate(
    cert_id: uuid.UUID,
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> Response:
    ok = await crud.delete_certificate(db, uuid.UUID(user.id), cert_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------ Browsing -------------------------------

@router.get("", response_model=list[TutorSummary])
async def browse_tutors(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, description="free text over headline/description"),
    category: str | None = None,
    language: str | None = None,
    country: str | None = None,
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    min_experience: int | None = Query(default=None, ge=0),
    native_speaker: bool = False,
    has_trial: bool = False,
    verified_only: bool = False,
    sort: str = Query(default="rating", pattern="^(rating|price_asc|price_desc|experience|reviews)$"),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[TutorSummary]:
    filters = TutorFilters(
        q=q,
        category=category,
        language=language,
        country=country,
        min_price_cents=min_price_cents,
        max_price_cents=max_price_cents,
        min_rating=min_rating,
        min_experience=min_experience,
        native_speaker=native_speaker,
        has_trial=has_trial,
        verified_only=verified_only,
        sort=sort,
    )
    tutors = await crud.browse(db, filters, limit=limit, offset=offset)
    return [TutorSummary.model_validate(t) for t in tutors]


@router.get("/{tutor_id}", response_model=TutorDetail)
async def get_tutor(tutor_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> TutorDetail:
    tutor = await crud.get(db, tutor_id)
    if tutor is None:
        raise HTTPException(status_code=404, detail="Tutor not found")
    return TutorDetail.model_validate(tutor)
