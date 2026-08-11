"""Password hashing + thin wrappers over the shared JWT helpers."""

from __future__ import annotations

from datetime import timedelta

from passlib.context import CryptContext

from edubridge_shared.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_token,
)

from .config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str) -> tuple[str, str]:
    settings = get_settings()
    return create_token(
        subject=user_id,
        role=role,
        token_type=ACCESS_TOKEN_TYPE,
        secret_key=settings.jwt_private_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str, role: str) -> tuple[str, str]:
    settings = get_settings()
    return create_token(
        subject=user_id,
        role=role,
        token_type=REFRESH_TOKEN_TYPE,
        secret_key=settings.jwt_private_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
