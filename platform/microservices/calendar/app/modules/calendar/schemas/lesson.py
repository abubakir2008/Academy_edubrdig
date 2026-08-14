"""Lesson schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LessonCreate(BaseModel):
    course_id: uuid.UUID
    scheduled_start: datetime
    duration_minutes: int = Field(ge=15, le=480)
    #: Optional — falls back to "Урок" if left blank.
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None


class LessonUpdate(BaseModel):
    scheduled_start: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=480)
    status: Literal["scheduled", "completed", "cancelled"] | None = None
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    course_id: uuid.UUID
    teacher_id: uuid.UUID
    series_id: uuid.UUID | None
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    title: str | None = None
    description: str | None = None
    created_at: datetime


class LessonConflict(BaseModel):
    scheduled_start: datetime
    scheduled_end: datetime
    conflicts_with: uuid.UUID


class LessonJoin(BaseModel):
    """Everything the frontend needs to connect to this lesson's LiveKit
    room — minted fresh on every request, not stored anywhere."""

    livekit_url: str
    token: str
    room: str


class RecordingOut(BaseModel):
    """A finished recording of one call session inside this lesson's room —
    a lesson can have more than one if the call was left and rejoined."""

    object_name: str
    url: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
