"""Calendar schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field


class RuleIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


class RuleOut(RuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class BlockedIn(BaseModel):
    start: datetime
    end: datetime
    reason: str | None = Field(default=None, max_length=255)


class BlockedOut(BlockedIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class Slot(BaseModel):
    start: datetime
    end: datetime
