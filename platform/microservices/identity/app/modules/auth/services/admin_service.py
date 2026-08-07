"""Admin-only user management: create/update/delete any account, issue and
rotate passwords. Distinct from `auth_service` (self-service register/login):
here an admin can assign staff roles and never needs the user's own password.
"""

from __future__ import annotations

import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import hash_password
from ..crud import user as user_crud
from ..models.user import User
from ..schemas.user import AdminUserCreate, AdminUserUpdate


def generate_password() -> str:
    return secrets.token_urlsafe(9)


async def list_users(db: AsyncSession, role: str | None) -> list[User]:
    return await user_crud.list_all(db, role)


async def create_user(db: AsyncSession, payload: AdminUserCreate) -> tuple[User, str]:
    existing = await user_crud.get_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    password = generate_password()
    user = await user_crud.create_user(
        db,
        email=payload.email,
        hashed_password=hash_password(password),
        full_name=payload.full_name,
        role=payload.role.value,
        is_verified=True,  # admin-created accounts skip email verification
    )
    return user, password


async def get_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await user_crud.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def update_user(db: AsyncSession, user: User, payload: AdminUserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "role" in data and data["role"] is not None:
        data["role"] = data["role"].value
    return await user_crud.update(db, user, data)


async def delete_user(db: AsyncSession, user: User) -> None:
    await user_crud.delete(db, user)


async def reset_password(db: AsyncSession, user: User) -> str:
    password = generate_password()
    await user_crud.update(db, user, {"hashed_password": hash_password(password)})
    return password
