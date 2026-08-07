"""User output schema."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from edubridge_shared.roles import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    referral_code: str
    created_at: datetime


class AdminUserOut(BaseModel):
    """Same shape as `UserOut` minus `referral_code` — irrelevant to admin
    user management, which cares about identity, role and account state."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: Role  # unlike self-registration, an admin may assign any role


class AdminUserCreated(BaseModel):
    """Returned exactly once, right after creation — there is no other way
    to retrieve a user's password afterwards (only bcrypt hashes are kept)."""

    user: AdminUserOut
    password: str


class AdminUserUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    # No `email` field: a user's login is immutable once the account exists.


class PasswordIssued(BaseModel):
    """Response of the reset-password action — the only way to "look up" a
    user's password is to rotate it and show the new one once."""

    password: str
