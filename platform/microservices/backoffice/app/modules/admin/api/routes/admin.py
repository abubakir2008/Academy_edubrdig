"""Admin endpoints (namespaced under /admin)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...db.session import get_db
from ...models.admin import AdminAction, Category, SystemSetting
from ..deps import require_roles

router = APIRouter(prefix="/admin", tags=["admin"])
require_admin = require_roles(Role.ADMIN, Role.SUPER_ADMIN)


# ------------------------------ Settings -------------------------------

class SettingIn(BaseModel):
    category: str = Field(default="general", max_length=64)
    value: dict = Field(default_factory=dict)


@router.get("/settings")
async def list_settings(
    _: CurrentUser = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    result = await db.execute(select(SystemSetting))
    return [{"key": s.key, "category": s.category, "value": s.value} for s in result.scalars()]


@router.put("/settings/{key}")
async def upsert_setting(
    key: str,
    payload: SettingIn,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = (
        pg_insert(SystemSetting)
        .values(key=key, category=payload.category, value=payload.value)
        .on_conflict_do_update(
            index_elements=[SystemSetting.key],
            set_={"category": payload.category, "value": payload.value},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"key": key, "category": payload.category, "value": payload.value}


# ----------------------------- Categories ------------------------------

class CategoryIn(BaseModel):
    slug: str = Field(max_length=128)
    name: str = Field(max_length=128)
    group: str | None = Field(default=None, max_length=64)
    seo_title: str | None = None
    seo_description: str | None = None


class CategoryOut(CategoryIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    payload: CategoryIn,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    exists = await db.execute(select(Category).where(Category.slug == payload.slug))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Category slug already exists")
    cat = Category(**payload.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[CategoryOut]:
    result = await db.execute(select(Category).order_by(Category.name))
    return [CategoryOut.model_validate(c) for c in result.scalars()]


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryIn,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CategoryOut:
    cat = await db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")
    for field, value in payload.model_dump().items():
        setattr(cat, field, value)
    await db.commit()
    await db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.delete("/categories/{category_id}", status_code=204, response_class=Response)
async def delete_category(
    category_id: uuid.UUID,
    _: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    cat = await db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------- Audit & dashboard -------------------------

@router.get("/actions")
async def list_actions(
    _: CurrentUser = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    result = await db.execute(
        select(AdminAction).order_by(AdminAction.created_at.desc()).limit(100)
    )
    return [
        {
            "id": str(a.id),
            "admin_id": str(a.admin_id),
            "action": a.action,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "details": a.details,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars()
    ]


@router.get("/dashboard")
async def dashboard(
    _: CurrentUser = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> dict:
    settings_count = await db.scalar(select(func.count(SystemSetting.key)))
    categories_count = await db.scalar(select(func.count(Category.id)))
    actions_count = await db.scalar(select(func.count(AdminAction.id)))
    return {
        "settings": int(settings_count or 0),
        "categories": int(categories_count or 0),
        "admin_actions": int(actions_count or 0),
        "note": "Cross-service KPIs (revenue, DAU, lessons) are served by the Analytics service.",
    }
