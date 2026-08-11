"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.schemas import MessageResponse

from ...crud import user as user_crud
from ...db.session import get_db
from ...models.user import User
from ...schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
)
from ...schemas.user import UserOut
from ...services import auth_service, token_store
from ...services.oauth import OAuthError, verify_apple
from ..deps import get_current_db_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    return await auth_service.login(db, payload)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    return await auth_service.refresh(db, payload.refresh_token)


class OAuthLogin(BaseModel):
    id_token: str


@router.post("/oauth/apple", response_model=TokenPair)
async def oauth_apple(payload: OAuthLogin, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        _subject, email = verify_apple(payload.id_token)
    except OAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return await auth_service.oauth_login(db, email=email)


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: RefreshRequest) -> MessageResponse:
    await auth_service.logout(payload.refresh_token)
    return MessageResponse(detail="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(current: User = Depends(get_current_db_user)) -> MessageResponse:
    await token_store.revoke_all(str(current.id))
    return MessageResponse(detail="Logged out from all sessions")


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_db_user)) -> User:
    return current
