"""Lesson & homework schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LessonCreate(BaseModel):
    booking_id: uuid.UUID | None = None
    student_id: uuid.UUID
    tutor_id: uuid.UUID
    subject: str | None = Field(default=None, max_length=64)
    scheduled_start: datetime
    duration_minutes: int = Field(default=60, ge=15, le=240)


class NotesUpdate(BaseModel):
    tutor_notes: str | None = None
    student_notes: str | None = None


class RecordingUpdate(BaseModel):
    recording_url: str = Field(max_length=1024)


class HomeworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    lesson_id: uuid.UUID
    title: str
    description: str | None
    due_date: datetime | None
    status: str
    submission_text: str | None
    grade: str | None
    feedback: str | None


class HomeworkCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None
    due_date: datetime | None = None


class HomeworkSubmit(BaseModel):
    submission_text: str


class HomeworkGrade(BaseModel):
    grade: str = Field(max_length=16)
    feedback: str | None = None


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    booking_id: uuid.UUID | None
    student_id: uuid.UUID
    tutor_id: uuid.UUID
    subject: str | None
    scheduled_start: datetime
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_minutes: int
    recording_url: str | None
    tutor_notes: str | None
    student_notes: str | None
    homeworks: list[HomeworkOut]
