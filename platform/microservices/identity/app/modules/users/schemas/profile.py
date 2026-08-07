"""Profile request / response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=1024)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str | None = Field(default=None, max_length=64)
    native_language: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    bio: str | None = Field(default=None, max_length=2000)
    languages: list[str] | None = Field(default=None)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str | None
    avatar_url: str | None
    country: str | None
    timezone: str | None
    native_language: str | None
    phone: str | None
    bio: str | None
    languages: list[str]
    created_at: datetime
    updated_at: datetime
