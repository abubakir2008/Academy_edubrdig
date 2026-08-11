"""Lead schemas."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

# Permissive on purpose (international formats, spaces/dashes/parens) — this
# is the platform's only public unauthenticated write, so the bar is "reject
# obvious garbage" (letters, single digits, essays), not "match one country's
# exact format."
_PHONE_RE = re.compile(r"^\+?[0-9][0-9 ()\-]{5,19}$")


class LeadCreate(BaseModel):
    subject: str | None = Field(default=None, max_length=255)
    goal: str | None = Field(default=None, max_length=255)
    date_of_birth: date | None = None
    study_place: str | None = Field(default=None, max_length=255)
    destination_country: str | None = Field(default=None, max_length=255)

    full_name: str = Field(min_length=1, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_email: EmailStr | None = None

    @field_validator("full_name")
    @classmethod
    def _full_name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("full_name can't be blank")
        return v

    @field_validator("contact_phone")
    @classmethod
    def _valid_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _PHONE_RE.fullmatch(v):
            raise ValueError("Not a valid phone number")
        return v

    @field_validator("contact_email", mode="after")
    @classmethod
    def _normalize_email(cls, v: str | None) -> str | None:
        # Lowercased so "Ann@Example.com" and "ann@example.com" dedupe as
        # the same person instead of slipping past the spam check below.
        return v.lower() if v else v

    @field_validator("date_of_birth")
    @classmethod
    def _plausible_birth_date(cls, v: date | None) -> date | None:
        if v is None:
            return None
        today = datetime.now(tz=timezone.utc).date()
        if v > today:
            raise ValueError("date_of_birth can't be in the future")
        if v < date.fromordinal(today.toordinal() - 120 * 365):
            raise ValueError("date_of_birth is implausibly old")
        return v

    @model_validator(mode="after")
    def _needs_a_way_to_reply(self) -> "LeadCreate":
        # This endpoint has no auth to fall back on — a lead with neither
        # contact field is unreachable and not worth storing.
        if not (self.contact_phone or "").strip() and not self.contact_email:
            raise ValueError("Provide at least a phone or an email")
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
    status: str
    created_at: datetime


class LeadStatusUpdate(BaseModel):
    status: Literal["new", "contacted", "closed"]
