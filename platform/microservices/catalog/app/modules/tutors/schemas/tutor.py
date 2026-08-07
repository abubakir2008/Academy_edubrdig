"""Tutor request / response schemas."""

from __future__ import annotations

import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict, Field


class WorkingHourIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


class WorkingHourOut(WorkingHourIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class CertificateIn(BaseModel):
    title: str = Field(max_length=255)
    issued_by: str | None = Field(default=None, max_length=255)
    year: int | None = Field(default=None, ge=1900, le=2100)
    file_url: str | None = Field(default=None, max_length=1024)


class CertificateOut(CertificateIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class TutorUpsert(BaseModel):
    headline: str | None = Field(default=None, max_length=255)
    description: str | None = None
    video_url: str | None = Field(default=None, max_length=1024)
    photo_url: str | None = Field(default=None, max_length=1024)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    native_language: str | None = Field(default=None, max_length=32)
    languages_taught: list[str] | None = None
    specializations: list[str] | None = None
    experience_years: int | None = Field(default=None, ge=0, le=80)
    price_cents: int | None = Field(default=None, ge=0)
    trial_price_cents: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None


class TutorSummary(BaseModel):
    """Compact representation used in browse / search results."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    headline: str | None
    photo_url: str | None
    country: str | None
    native_language: str | None
    languages_taught: list[str]
    specializations: list[str]
    experience_years: int
    price_cents: int
    trial_price_cents: int | None
    currency: str
    is_verified: bool
    rating: float
    total_reviews: int
    total_lessons: int


class TutorDetail(TutorSummary):
    description: str | None
    video_url: str | None
    is_active: bool
    working_hours: list[WorkingHourOut]
    certificates: list[CertificateOut]
