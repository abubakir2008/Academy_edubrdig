"""Student request / response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StudentUpdate(BaseModel):
    learning_goals: str | None = None
    learning_languages: list[str] | None = None
    level: str | None = Field(default=None, max_length=32)


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tutor_id: uuid.UUID
    created_at: datetime


class ProgressUpsert(BaseModel):
    subject: str = Field(max_length=64)
    lessons_completed: int = Field(default=0, ge=0)
    hours_spent: int = Field(default=0, ge=0)
    notes: str | None = None


class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    subject: str
    lessons_completed: int
    hours_spent: int
    notes: str | None
    updated_at: datetime


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    learning_goals: str | None
    learning_languages: list[str]
    level: str | None
    favorites: list[FavoriteOut]
    progress: list[ProgressOut]


class LeadCreate(BaseModel):
    """Intake form submission. Anonymous — a name and a way to reach the
    person are the point, since there may be no account yet."""

    subject: str | None = Field(default=None, max_length=64)
    goal: str | None = Field(default=None, max_length=64)
    date_of_birth: date | None = None
    study_place: str | None = Field(default=None, max_length=255)
    destination_country: str | None = Field(default=None, max_length=64)
    full_name: str = Field(max_length=255, min_length=1)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _require_a_contact_method(self) -> "LeadCreate":
        if not self.contact_phone and not self.contact_email:
            raise ValueError("Укажите телефон или email")
        return self


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    subject: str | None
    goal: str | None
    date_of_birth: date | None
    study_place: str | None
    destination_country: str | None
    full_name: str
    contact_phone: str | None
    contact_email: str | None
    created_at: datetime
