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
    #: Optional — falls back to "Урок" (also used as the Zoom meeting topic
    #: when set) if left blank.
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
    #: Join link — present for everyone who can see the lesson.
    meeting_url: str | None = None
    #: Host-start link — only ever populated for the lesson's own teacher or
    #: staff; the route blanks it out for anyone else before responding.
    start_url: str | None = None


class LessonConflict(BaseModel):
    scheduled_start: datetime
    scheduled_end: datetime
    conflicts_with: uuid.UUID


class ZoomStatus(BaseModel):
    connected: bool
    email: str | None = None


class ZoomAuthorizeUrl(BaseModel):
    authorize_url: str
