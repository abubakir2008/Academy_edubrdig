"""CMS endpoints (namespaced under /cms)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import content as crud
from ...db.session import get_db
from ...schemas.content import ArticleCreate, ArticleOut, ArticleUpdate
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/cms", tags=["cms"])
require_editor = require_roles(Role.CONTENT_MANAGER, Role.ADMIN, Role.SUPER_ADMIN)


@router.post("/articles", response_model=ArticleOut, status_code=201)
async def create_article(
    payload: ArticleCreate,
    user: CurrentUser = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> ArticleOut:
    if await crud.get_by_slug(db, payload.slug):
        raise HTTPException(status_code=409, detail="Slug already exists")
    article = await crud.create(db, uuid.UUID(user.id), payload.model_dump())
    return ArticleOut.model_validate(article)


@router.get("/articles", response_model=list[ArticleOut])
async def list_articles(
    type: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ArticleOut]:
    # Public listing only returns published content.
    items = await crud.list_articles(db, type, only_published=True, limit=limit, offset=offset)
    return [ArticleOut.model_validate(a) for a in items]


@router.get("/articles/{slug}", response_model=ArticleOut)
async def get_article(slug: str, db: AsyncSession = Depends(get_db)) -> ArticleOut:
    article = await crud.get_by_slug(db, slug)
    if article is None or not article.published:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleOut.model_validate(article)


@router.put("/articles/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: uuid.UUID,
    payload: ArticleUpdate,
    _: CurrentUser = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> ArticleOut:
    article = await crud.get(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(article, field, value)
    return ArticleOut.model_validate(await crud.save(db, article))


@router.delete("/articles/{article_id}", status_code=204, response_class=Response)
async def delete_article(
    article_id: uuid.UUID,
    _: CurrentUser = Depends(require_editor),
    db: AsyncSession = Depends(get_db),
) -> Response:
    article = await crud.get(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    await crud.delete(db, article)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
