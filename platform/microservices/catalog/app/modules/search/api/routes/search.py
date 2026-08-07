"""Search endpoints (namespaced under /search).

Used to query a separate ElasticSearch index that was kept in sync via a
Kafka reindex — a whole extra container, plus a replication lag window,
purely so text search could exist. Now Search lives in the same department
and the same database as Tutors, so it queries the tutor table directly with
Postgres full-text search (see ``tutors/models/tutor.py::search_vector``).
There is nothing left to reindex: a write to a tutor row *is* the index
update, atomically, for free.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Query

from ....tutors.crud import tutor as tutor_crud
from ....tutors.crud.tutor import TutorFilters
from ....tutors.db.session import get_db
from ....tutors.schemas.tutor import TutorSummary

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/tutors")
async def search_tutors(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None),
    language: str | None = None,
    category: str | None = None,
    country: str | None = None,
    min_price_cents: int | None = None,
    max_price_cents: int | None = None,
    min_rating: float | None = None,
    native_speaker: bool = False,
    verified_only: bool = False,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    filters = TutorFilters(
        q=q,
        category=category,
        language=language,
        country=country,
        min_price_cents=min_price_cents,
        max_price_cents=max_price_cents,
        min_rating=min_rating,
        native_speaker=native_speaker,
        verified_only=verified_only,
    )
    tutors = await tutor_crud.browse(db, filters, limit=limit, offset=offset)
    total = await tutor_crud.count(db, filters)
    return {
        "total": total,
        "results": [TutorSummary.model_validate(t).model_dump(mode="json") for t in tutors],
    }
