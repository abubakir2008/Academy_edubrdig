"""Student endpoints (namespaced under /students)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import student as crud
from ...db.session import get_db
from ...schemas.student import (
    FavoriteOut,
    LeadCreate,
    LeadOut,
    ProgressOut,
    ProgressUpsert,
    StudentOut,
    StudentUpdate,
)
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/students", tags=["students"])
require_admin = require_roles(Role.ADMIN, Role.SUPER_ADMIN)


@router.get("/me", response_model=StudentOut)
async def get_me(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentOut:
    student = await crud.get_or_create(db, uuid.UUID(user.id))
    return StudentOut.model_validate(student)


@router.put("/me", response_model=StudentOut)
async def update_me(
    payload: StudentUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentOut:
    student = await crud.get_or_create(db, uuid.UUID(user.id))
    student = await crud.update(db, student, payload.model_dump(exclude_unset=True))
    return StudentOut.model_validate(student)


@router.get("/me/favorites", response_model=list[FavoriteOut])
async def list_favorites(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FavoriteOut]:
    student = await crud.get_or_create(db, uuid.UUID(user.id))
    return [FavoriteOut.model_validate(f) for f in student.favorites]


@router.post("/me/favorites/{tutor_id}", response_model=FavoriteOut, status_code=201)
async def add_favorite(
    tutor_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FavoriteOut:
    await crud.get_or_create(db, uuid.UUID(user.id))
    fav = await crud.add_favorite(db, uuid.UUID(user.id), tutor_id)
    return FavoriteOut.model_validate(fav)


@router.delete(
    "/me/favorites/{tutor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def remove_favorite(
    tutor_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    ok = await crud.remove_favorite(db, uuid.UUID(user.id), tutor_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/me/progress", response_model=ProgressOut)
async def upsert_progress(
    payload: ProgressUpsert,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressOut:
    await crud.get_or_create(db, uuid.UUID(user.id))
    entry = await crud.upsert_progress(db, uuid.UUID(user.id), payload.model_dump())
    return ProgressOut.model_validate(entry)


# ------------------------------ Intake leads -----------------------------
# Anonymous by design: the onboarding form works for visitors with no
# account, which is exactly why it collects a name and a contact method.


@router.post("/leads", response_model=LeadOut, status_code=201)
async def submit_lead(
    payload: LeadCreate,
    db: AsyncSession = Depends(get_db),
) -> LeadOut:
    lead = await crud.create_lead(db, payload.model_dump())
    return LeadOut.model_validate(lead)


@router.get("/leads", response_model=list[LeadOut])
async def list_leads(
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[LeadOut]:
    leads = await crud.list_leads(db)
    return [LeadOut.model_validate(lead) for lead in leads]
