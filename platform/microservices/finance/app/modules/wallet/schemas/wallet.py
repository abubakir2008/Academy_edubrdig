"""Wallet schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WalletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tutor_id: uuid.UUID
    balance_cents: int
    currency: str


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    amount_cents: int
    balance_after_cents: int
    reference: str | None
    description: str | None
    created_at: datetime


class CreditRequest(BaseModel):
    tutor_id: uuid.UUID
    amount_cents: int = Field(gt=0)
    reference: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=255)


class WithdrawalRequest(BaseModel):
    amount_cents: int = Field(gt=0)
    method: str = Field(default="bank_card", pattern="^(bank_card|mobile_wallet|crypto|paypal)$")
    destination: str = Field(max_length=255, description="card/wallet/account number or address")


class WithdrawalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tutor_id: uuid.UUID
    amount_cents: int
    currency: str
    method: str
    destination: str | None
    status: str
    note: str | None
    created_at: datetime
