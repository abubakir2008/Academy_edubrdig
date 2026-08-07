"""CMS persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.content import Article


async def create(db: AsyncSession, author_id: uuid.UUID, data: dict) -> Article:
    article = Article(author_id=author_id, **data)
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


async def get(db: AsyncSession, article_id: uuid.UUID) -> Article | None:
    return await db.get(Article, article_id)


async def get_by_slug(db: AsyncSession, slug: str) -> Article | None:
    result = await db.execute(select(Article).where(Article.slug == slug))
    return result.scalar_one_or_none()


async def list_articles(
    db: AsyncSession, type_: str | None, only_published: bool, limit: int, offset: int
) -> list[Article]:
    stmt = select(Article)
    if type_:
        stmt = stmt.where(Article.type == type_)
    if only_published:
        stmt = stmt.where(Article.published.is_(True))
    stmt = stmt.order_by(Article.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def save(db: AsyncSession, article: Article) -> Article:
    await db.commit()
    await db.refresh(article)
    return article


async def delete(db: AsyncSession, article: Article) -> None:
    await db.delete(article)
    await db.commit()
