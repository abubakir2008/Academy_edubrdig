"""Profile request / response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=1024)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    bio_short: str | None = Field(default=None, max_length=280)
    bio_full: str | None = None
    languages: list[str] | None = None
    category_ids: list[uuid.UUID] | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


class TutorOut(BaseModel):
    """Public tutor card — `/users/tutors`. Deliberately excludes bio_full
    (only shown on the tutor's own full profile, `/users/tutors/{id}`)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    full_name: str | None
    avatar_url: str | None
    experience_years: int | None
    bio_short: str | None
    languages: list[str] | None
    category_ids: list[uuid.UUID] | None


class TutorDetailOut(TutorOut):
    bio_full: str | None
