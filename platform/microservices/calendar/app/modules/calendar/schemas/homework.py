"""Homework schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HomeworkCreate(BaseModel):
    student_id: uuid.UUID
    title: str = Field(max_length=200)
    description: str | None = None
    due_date: datetime | None = None
    #: Optional — grade what just happened in the call (e.g. spoken
    #: practice) at the same time as assigning the written follow-up.
    grade: float | None = None
    comment: str | None = None


class HomeworkSubmit(BaseModel):
    submission_url: str = Field(max_length=500)
    submission_note: str | None = None


class HomeworkGrade(BaseModel):
    grade: float
    comment: str | None = None


class HomeworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    lesson_id: uuid.UUID
    course_id: uuid.UUID
    teacher_id: uuid.UUID
    student_id: uuid.UUID
    title: str
    description: str | None
    due_date: datetime | None
    status: str
    submission_url: str | None
    submission_note: str | None
    submitted_at: datetime | None
    grade: float | None
    comment: str | None
    graded_at: datetime | None
    created_at: datetime
