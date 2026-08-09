"""Admin endpoints (namespaced under /admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...db.session import get_db
from ...models.admin import AdminAction, SystemSetting
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
    actions_count = await db.scalar(select(func.count(AdminAction.id)))
    return {
        "settings": int(settings_count or 0),
        "admin_actions": int(actions_count or 0),
        "note": "Cross-service KPIs (revenue, DAU, lessons) are served by the Analytics service.",
    }
