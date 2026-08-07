"""Admin-only user management (namespaced under /auth/admin/users).

Lives in the `auth` module because that's where the `User` model lives, and
mounted under `/auth` (not `/admin`) because Traefik routes `/api/admin/*`
to the backoffice department, not identity — `/api/auth/*` is already wired
to this service.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...db.session import get_db
from ...schemas.user import (
    AdminUserCreate,
    AdminUserCreated,
    AdminUserOut,
    AdminUserUpdate,
    PasswordIssued,
)
from ...services import admin_service
from ..deps import require_roles

router = APIRouter(prefix="/auth/admin/users", tags=["admin-users"])
require_admin = require_roles(Role.ADMIN, Role.SUPER_ADMIN)


@router.get("", response_model=list[AdminUserOut])
async def list_users(
    role: str | None = Query(default=None),
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserOut]:
    users = await admin_service.list_users(db, role)
    return [AdminUserOut.model_validate(u) for u in users]


@router.post("", response_model=AdminUserCreated, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserCreated:
    user, password = await admin_service.create_user(db, payload)
    return AdminUserCreated(user=AdminUserOut.model_validate(user), password=password)


@router.put("/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminUserOut:
    user = await admin_service.get_or_404(db, user_id)
    user = await admin_service.update_user(db, user, payload)
    return AdminUserOut.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_user(
    user_id: uuid.UUID,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    user = await admin_service.get_or_404(db, user_id)
    await admin_service.delete_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/reset-password", response_model=PasswordIssued)
async def reset_password(
    user_id: uuid.UUID,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PasswordIssued:
    user = await admin_service.get_or_404(db, user_id)
    password = await admin_service.reset_password(db, user)
    return PasswordIssued(password=password)
