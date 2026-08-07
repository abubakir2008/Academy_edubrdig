"""Payment schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CheckoutRequest(BaseModel):
    # Only the booking id is trusted from the client; the amount, tutor and
    # currency are resolved server-side from the authoritative booking record.
    booking_id: uuid.UUID


class CheckoutResponse(BaseModel):
    payment_id: uuid.UUID
    status: str
    amount_cents: int
    currency: str
    # Present when the gateway needs a redirect (real PSP); null for the mock.
    payment_url: str | None = None


class RefundRequest(BaseModel):
    amount_cents: int | None = Field(default=None, gt=0, description="defaults to full amount")
    reason: str | None = Field(default=None, max_length=500)


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    amount_cents: int
    reason: str | None
    status: str
    created_at: datetime


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    student_id: uuid.UUID
    tutor_id: uuid.UUID
    booking_id: uuid.UUID | None
    quantity: int
    amount_cents: int
    currency: str
    commission_rate: float
    commission_cents: int
    tutor_earnings_cents: int
    status: str
    gateway: str
    created_at: datetime
    refunds: list[RefundOut]


class PackageCheckoutRequest(BaseModel):
    tutor_id: uuid.UUID
    lesson_count: int = Field(ge=5, le=40, description="5, 10, 20 or 40 — see discount tiers")


class LessonPackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tutor_id: uuid.UUID
    student_id: uuid.UUID
    total_lessons: int
    lessons_remaining: int
    price_cents: int
    currency: str
    created_at: datetime


class Receipt(BaseModel):
    payment_id: uuid.UUID
    issued_at: datetime
    student_id: uuid.UUID
    tutor_id: uuid.UUID
    quantity: int
    amount_cents: int
    currency: str
    commission_cents: int
    tutor_earnings_cents: int
    status: str
