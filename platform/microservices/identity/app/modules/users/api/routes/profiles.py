"""User profile endpoints (namespaced under /users)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import STAFF_ROLES

from ...crud import profile as crud
from ...db.session import get_db
from ...schemas.profile import ProfileOut, ProfileUpdate
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    profile = await crud.get_or_create(db, uuid.UUID(user.id))
    return ProfileOut.model_validate(profile)


@router.put("/me", response_model=ProfileOut)
async def update_my_profile(
    payload: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    profile = await crud.get_or_create(db, uuid.UUID(user.id))
    data = payload.model_dump(exclude_unset=True)
    profile = await crud.update(db, profile, data)
    return ProfileOut.model_validate(profile)


@router.get("/{user_id}", response_model=ProfileOut)
async def get_public_profile(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ProfileOut:
    profile = await crud.get(db, user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ProfileOut.model_validate(profile)


@router.get("", response_model=list[ProfileOut])
async def list_profiles(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles(*STAFF_ROLES)),
) -> list[ProfileOut]:
    profiles = await crud.list_profiles(db, limit=limit, offset=offset)
    return [ProfileOut.model_validate(p) for p in profiles]
