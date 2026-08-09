"""Course schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class TeacherAssign(BaseModel):
    teacher_id: uuid.UUID | None = None


class EnrollmentCreate(BaseModel):
    student_id: uuid.UUID


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str | None
    teacher_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class CourseDetail(CourseOut):
    student_ids: list[uuid.UUID]
