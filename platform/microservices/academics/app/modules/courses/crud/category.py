"""Category persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.category import Category


async def create(db: AsyncSession, name: str, slug: str) -> Category:
    category = Category(name=name, slug=slug)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def get(db: AsyncSession, category_id: uuid.UUID) -> Category | None:
    return await db.get(Category, category_id)


async def list_all(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).order_by(Category.name))
    return list(result.scalars().all())


async def update(db: AsyncSession, category: Category, data: dict) -> Category:
    for field, value in data.items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete(db: AsyncSession, category: Category) -> None:
    await db.delete(category)
    await db.commit()
