"""Database access + filtered browsing for tutors."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.tutor import Certificate, Tutor, WorkingHour


@dataclass
class TutorFilters:
    q: str | None = None
    category: str | None = None
    language: str | None = None
    country: str | None = None
    min_price_cents: int | None = None
    max_price_cents: int | None = None
    min_rating: float | None = None
    min_experience: int | None = None
    native_speaker: bool = False
    has_trial: bool = False
    verified_only: bool = False
    sort: str = "rating"  # rating | price_asc | price_desc | experience | reviews


async def get(db: AsyncSession, tutor_id: uuid.UUID) -> Tutor | None:
    return await db.get(Tutor, tutor_id)


async def get_or_create(db: AsyncSession, tutor_id: uuid.UUID) -> Tutor:
    tutor = await db.get(Tutor, tutor_id)
    if tutor is None:
        tutor = Tutor(user_id=tutor_id, languages_taught=[], specializations=[])
        db.add(tutor)
        await db.commit()
        await db.refresh(tutor)
    return tutor


async def update(db: AsyncSession, tutor: Tutor, data: dict) -> Tutor:
    for field, value in data.items():
        setattr(tutor, field, value)
    await db.commit()
    await db.refresh(tutor)
    return tutor


def _apply_filters(stmt: Select, f: TutorFilters) -> Select:
    # Only list tutors that are accepting students.
    stmt = stmt.where(Tutor.is_active.is_(True))

    if f.verified_only:
        stmt = stmt.where(Tutor.is_verified.is_(True))
    if f.country:
        stmt = stmt.where(Tutor.country == f.country.upper())
    if f.category:
        stmt = stmt.where(Tutor.specializations.any(f.category))
    if f.language:
        stmt = stmt.where(Tutor.languages_taught.any(f.language))
        if f.native_speaker:
            stmt = stmt.where(Tutor.native_language == f.language)
    elif f.native_speaker:
        # Native speaker requested without a specific language -> no-op guard.
        pass
    if f.min_price_cents is not None:
        stmt = stmt.where(Tutor.price_cents >= f.min_price_cents)
    if f.max_price_cents is not None:
        stmt = stmt.where(Tutor.price_cents <= f.max_price_cents)
    if f.min_rating is not None:
        stmt = stmt.where(Tutor.rating >= f.min_rating)
    if f.min_experience is not None:
        stmt = stmt.where(Tutor.experience_years >= f.min_experience)
    if f.has_trial:
        stmt = stmt.where(Tutor.trial_price_cents.is_not(None))
    if f.q:
        # Full-text match against the generated search_vector (see the model):
        # ranked, stemmed, and indexed — this replaced a whole separate
        # ElasticSearch container that existed only for this one query.
        stmt = stmt.where(Tutor.search_vector.op("@@")(func.websearch_to_tsquery("simple", f.q)))

    sort_map = {
        "rating": Tutor.rating.desc(),
        "price_asc": Tutor.price_cents.asc(),
        "price_desc": Tutor.price_cents.desc(),
        "experience": Tutor.experience_years.desc(),
        "reviews": Tutor.total_reviews.desc(),
    }
    if f.q and f.sort == "rating":
        # A text query defaults to relevance order rather than rating order,
        # unless the caller explicitly asked for a different sort.
        rank = func.ts_rank(Tutor.search_vector, func.websearch_to_tsquery("simple", f.q))
        return stmt.order_by(rank.desc())
    return stmt.order_by(sort_map.get(f.sort, Tutor.rating.desc()))


async def browse(
    db: AsyncSession, f: TutorFilters, limit: int, offset: int
) -> list[Tutor]:
    stmt = _apply_filters(select(Tutor), f).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def count(db: AsyncSession, f: TutorFilters) -> int:
    # order_by(None): _apply_filters attaches a relevance/rating ORDER BY,
    # which is meaningless for a count — and when it's ts_rank(search_vector,
    # ...), Postgres treats it as an ungrouped column against the aggregate
    # count() and rejects the query outright.
    stmt = _apply_filters(select(func.count(Tutor.user_id)), f).order_by(None)
    result = await db.execute(stmt)
    return int(result.scalar_one())


# ---- Working hours ----

async def replace_working_hours(
    db: AsyncSession, tutor: Tutor, hours: list[dict]
) -> Tutor:
    tutor.working_hours.clear()
    for h in hours:
        tutor.working_hours.append(WorkingHour(**h))
    await db.commit()
    await db.refresh(tutor)
    return tutor


# ---- Certificates ----

async def add_certificate(db: AsyncSession, tutor_id: uuid.UUID, data: dict) -> Certificate:
    cert = Certificate(tutor_id=tutor_id, **data)
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


async def delete_certificate(
    db: AsyncSession, tutor_id: uuid.UUID, cert_id: uuid.UUID
) -> bool:
    cert = await db.get(Certificate, cert_id)
    if cert is None or cert.tutor_id != tutor_id:
        return False
    await db.delete(cert)
    await db.commit()
    return True
