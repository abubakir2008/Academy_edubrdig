"""Core authentication use-cases: register, login, refresh, logout."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.security import (
    REFRESH_TOKEN_TYPE,
    TokenError,
    decode_token,
)

from ..core.config import get_settings
from ..core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from ..crud import user as user_crud
from ..models.user import User
from ..schemas.auth import LoginRequest, TokenPair
from . import token_store

_settings = get_settings()


async def _issue_token_pair(user: User) -> TokenPair:
    access, _ = create_access_token(str(user.id), user.role)
    refresh, refresh_jti = create_refresh_token(str(user.id), user.role)
    await token_store.store_refresh(str(user.id), refresh_jti)
    return TokenPair(access_token=access, refresh_token=refresh)


async def login(db: AsyncSession, payload: LoginRequest) -> TokenPair:
    user = await user_crud.get_by_email(db, payload.email)
    if (
        user is None
        or user.hashed_password is None
        # bcrypt is deliberately slow (100-300ms) — run it off the event loop
        # so one login doesn't stall every other concurrent request.
        or not await asyncio.to_thread(verify_password, payload.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    return await _issue_token_pair(user)


async def refresh(db: AsyncSession, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(
            refresh_token,
            secret_key=_settings.jwt_public_key,
            algorithm=_settings.jwt_algorithm,
            expected_type=REFRESH_TOKEN_TYPE,
        )
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    if not await token_store.is_valid_refresh(payload.sub, payload.jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    # Rotation: old refresh token is invalidated, a fresh pair is issued.
    await token_store.revoke_refresh(payload.sub, payload.jti)

    import uuid

    user = await user_crud.get_by_id(db, uuid.UUID(payload.sub))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return await _issue_token_pair(user)


async def oauth_login(db: AsyncSession, *, email: str) -> TokenPair:
    """Log in with a verified OAuth identity — for an *existing* account only.

    Accounts are admin-created now (see /auth/admin/users); a verified Apple
    identity is not, by itself, authorization to create one.
    """
    user = await user_crud.get_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found — ask an administrator to create one",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return await _issue_token_pair(user)


async def logout(refresh_token: str) -> None:
    try:
        payload = decode_token(
            refresh_token,
            secret_key=_settings.jwt_public_key,
            algorithm=_settings.jwt_algorithm,
            expected_type=REFRESH_TOKEN_TYPE,
        )
    except TokenError:
        # Logging out with an already-invalid token is a no-op success.
        return
    await token_store.revoke_refresh(payload.sub, payload.jti)
