"""Booking schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookingCreate(BaseModel):
    tutor_id: uuid.UUID
    scheduled_start: datetime
    duration_minutes: int = Field(default=60, ge=15, le=240)
    is_trial: bool = False
    # Price is NOT accepted from the client — it is resolved server-side from the
    # tutor's profile so a caller can't pay an arbitrary amount.
    # When set, this lesson draws down an already-paid-for package instead of
    # needing its own /payments/checkout — Finance verifies ownership and
    # remaining credit itself, Booking never touches the package's balance.
    package_id: uuid.UUID | None = None


class BookingReschedule(BaseModel):
    scheduled_start: datetime
    duration_minutes: int | None = Field(default=None, ge=15, le=240)


class BookingCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    tutor_id: uuid.UUID
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int
    is_trial: bool
    status: str
    price_cents: int
    currency: str
    payment_id: uuid.UUID | None
    lesson_id: uuid.UUID | None
    package_id: uuid.UUID | None
    cancel_reason: str | None
    created_at: datetime
