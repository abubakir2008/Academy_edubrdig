"""Review schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    tutor_id: uuid.UUID
    # Required: a review must point at a real, completed lesson with this
    # tutor — enforced against the Lessons module, see routes/reviews.py.
    lesson_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    author_id: uuid.UUID
    tutor_id: uuid.UUID
    lesson_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime


class ReviewSummary(BaseModel):
    tutor_id: uuid.UUID
    average_rating: float
    total_reviews: int


class ComplaintCreate(BaseModel):
    target_type: str = Field(pattern="^(tutor|review)$")
    target_id: uuid.UUID
    reason: str = Field(min_length=3)


class ComplaintResolve(BaseModel):
    status: str = Field(pattern="^(reviewed|resolved|dismissed)$")
    resolution: str | None = None


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    author_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    reason: str
    status: str
    resolution: str | None
    created_at: datetime
