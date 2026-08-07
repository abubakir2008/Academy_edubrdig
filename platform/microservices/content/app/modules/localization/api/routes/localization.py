"""Localization endpoints (namespaced under /localization)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...db.session import get_db
from ...models.localization import Language, Translation
from ..deps import require_roles

router = APIRouter(prefix="/localization", tags=["localization"])
require_staff = require_roles(Role.CONTENT_MANAGER, Role.ADMIN, Role.SUPER_ADMIN)


class LanguageIn(BaseModel):
    code: str = Field(min_length=2, max_length=8)
    name: str = Field(max_length=64)
    is_active: bool = True


class TranslationIn(BaseModel):
    locale: str = Field(min_length=2, max_length=8)
    key: str = Field(max_length=255)
    value: str


@router.get("/languages")
async def list_languages(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Language).order_by(Language.code))
    return [{"code": l.code, "name": l.name, "is_active": l.is_active} for l in result.scalars()]


@router.post("/languages", status_code=201)
async def upsert_language(
    payload: LanguageIn,
    _: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = (
        pg_insert(Language)
        .values(**payload.model_dump())
        .on_conflict_do_update(
            index_elements=[Language.code],
            set_={"name": payload.name, "is_active": payload.is_active},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return payload.model_dump()


@router.get("/translations")
async def get_translations(
    locale: str = Query(...), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    result = await db.execute(select(Translation).where(Translation.locale == locale))
    return {t.key: t.value for t in result.scalars()}


@router.put("/translations")
async def upsert_translation(
    payload: TranslationIn,
    _: CurrentUser = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = (
        pg_insert(Translation)
        .values(**payload.model_dump())
        .on_conflict_do_update(
            constraint="uq_locale_key",
            set_={"value": payload.value},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return payload.model_dump()
