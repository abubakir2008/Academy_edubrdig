"""CMS schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ArticleCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=255)
    type: str = Field(default="blog", pattern="^(blog|faq|page|policy|landing)$")
    title: str = Field(max_length=255)
    body: str = ""
    published: bool = False
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = Field(default=None, max_length=500)


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    body: str | None = None
    published: bool | None = None
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = Field(default=None, max_length=500)


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    type: str
    title: str
    body: str
    published: bool
    author_id: uuid.UUID | None
    seo_title: str | None
    seo_description: str | None
    created_at: datetime
    updated_at: datetime
