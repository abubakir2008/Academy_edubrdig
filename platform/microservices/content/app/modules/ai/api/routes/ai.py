"""AI endpoints (namespaced under /ai)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...core.config import get_settings
from ...db.session import get_db
from ...models.ai_log import AiRequestLog
from ...services import engine
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/ai", tags=["ai"])
_settings = get_settings()


async def _log(db: AsyncSession, user_id: uuid.UUID, feature: str, summary: str) -> None:
    db.add(AiRequestLog(user_id=user_id, feature=feature, input_summary=summary[:500]))
    await db.commit()


async def _enforce_daily_limit(db: AsyncSession, user_id: uuid.UUID) -> None:
    """AI_DAILY_LIMIT caps model-backed calls per user per day — a real cap on
    Anthropic spend, not just a config field nobody reads. Counts the same
    AiRequestLog every call already writes, so it costs one extra query, not
    a new table."""
    since = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count = await db.scalar(
        select(func.count())
        .select_from(AiRequestLog)
        .where(AiRequestLog.user_id == user_id, AiRequestLog.created_at >= since)
    )
    if count is not None and count >= _settings.ai_daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily AI request limit ({_settings.ai_daily_limit}) reached",
        )


class HomeworkReq(BaseModel):
    subject: str
    level: str = "beginner"
    topic: str
    num_tasks: int = Field(default=3, ge=1, le=10)


class LessonAnalyzeReq(BaseModel):
    notes: str


class TopicExplainReq(BaseModel):
    subject: str
    level: str = "beginner"
    topic: str


class ProgressReq(BaseModel):
    lessons_completed: int = Field(ge=0)
    hours_spent: int = Field(ge=0)
    avg_rating: float = Field(default=0, ge=0, le=5)


class RecommendReq(BaseModel):
    candidates: list[dict] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)


@router.post("/homework/generate")
async def homework(
    payload: HomeworkReq,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _enforce_daily_limit(db, uuid.UUID(user.id))
    await _log(db, uuid.UUID(user.id), "homework", f"{payload.subject}:{payload.topic}")
    return await engine.generate_homework(payload.subject, payload.level, payload.topic, payload.num_tasks)


@router.post("/topic/explain")
async def topic_explain(
    payload: TopicExplainReq,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _enforce_daily_limit(db, uuid.UUID(user.id))
    await _log(db, uuid.UUID(user.id), "topic_explain", f"{payload.subject}:{payload.topic}")
    return await engine.explain_topic(payload.subject, payload.level, payload.topic)


@router.post("/lesson/analyze")
async def lesson_analyze(
    payload: LessonAnalyzeReq,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _enforce_daily_limit(db, uuid.UUID(user.id))
    await _log(db, uuid.UUID(user.id), "lesson_analyze", payload.notes[:80])
    return await engine.analyze_lesson(payload.notes)


@router.post("/progress/analyze")
async def progress_analyze(
    payload: ProgressReq,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _log(db, uuid.UUID(user.id), "progress", "")
    return engine.analyze_progress(payload.lessons_completed, payload.hours_spent, payload.avg_rating)


@router.post("/recommendations")
async def recommendations(
    payload: RecommendReq,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _log(db, uuid.UUID(user.id), "recommend", "")
    return {"results": engine.recommend_tutors(payload.candidates, payload.preferences)}


@router.get("/logs")
async def logs(
    limit: int = Query(default=50, le=200),
    _: CurrentUser = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(AiRequestLog).order_by(AiRequestLog.created_at.desc()).limit(limit)
    )
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "feature": r.feature,
            "input_summary": r.input_summary,
            "created_at": r.created_at.isoformat(),
        }
        for r in result.scalars()
    ]
