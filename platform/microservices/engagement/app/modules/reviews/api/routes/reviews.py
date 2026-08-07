"""Review & complaint endpoints (namespaced under /reviews)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.clients import ServiceClient, ServiceError, service_url
from edubridge_shared.events import Topics
from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import review as crud
from ...db.session import get_db
from ...events import bus
from ...models.review import ComplaintStatus
from ...schemas.review import (
    ComplaintCreate,
    ComplaintOut,
    ComplaintResolve,
    ReviewCreate,
    ReviewOut,
    ReviewSummary,
)
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/reviews", tags=["reviews"])
require_moderator = require_roles(Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN)
_lessons = ServiceClient(service_url("lessons"))


async def _verify_completed_lesson(
    *, lesson_id: uuid.UUID, tutor_id: uuid.UUID, student_id: uuid.UUID, token: str
) -> None:
    """A review must point at a real, completed lesson between these two people.

    Without this check any authenticated user could review any tutor an
    unlimited number of times, since nothing tied the review to an actual
    lesson — see the reviews module's history for the incident that motivated
    this. The Lessons module already enforces "only a participant can read
    this lesson", so passing the caller's own token both verifies and
    authorizes in one call.
    """
    try:
        lesson = await _lessons.get(f"/lessons/{lesson_id}", token=token)
    except ServiceError as exc:
        if exc.status == 404:
            raise HTTPException(status_code=404, detail="Lesson not found") from exc
        if exc.status == 403:
            raise HTTPException(status_code=403, detail="Not your lesson") from exc
        raise HTTPException(status_code=502, detail="Could not verify lesson") from exc
    if lesson.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Lesson is not completed yet")
    if lesson.get("tutor_id") != str(tutor_id) or lesson.get("student_id") != str(student_id):
        raise HTTPException(status_code=409, detail="Lesson does not match this tutor/student")


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(...),
) -> ReviewOut:
    token = authorization.removeprefix("Bearer ").strip()
    await _verify_completed_lesson(
        lesson_id=payload.lesson_id,
        tutor_id=payload.tutor_id,
        student_id=uuid.UUID(user.id),
        token=token,
    )
    try:
        review = await crud.create_review(db, uuid.UUID(user.id), payload.model_dump())
    except Exception as exc:  # unique violation -> already reviewed
        await db.rollback()
        raise HTTPException(status_code=409, detail="You already reviewed this lesson") from exc

    # Publish the fresh aggregate so the Tutor service can update its rating.
    avg, count = await crud.tutor_summary(db, review.tutor_id)
    await bus.publish(
        Topics.REVIEW_CREATED,
        {
            "review_id": str(review.id),
            "tutor_id": str(review.tutor_id),
            "author_id": str(review.author_id),
            "rating": review.rating,
            "average_rating": avg,
            "total_reviews": count,
        },
        key=str(review.tutor_id),
    )
    return ReviewOut.model_validate(review)


@router.get("/tutor/{tutor_id}", response_model=list[ReviewOut])
async def tutor_reviews(
    tutor_id: uuid.UUID,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewOut]:
    reviews = await crud.list_for_tutor(db, tutor_id, limit, offset)
    return [ReviewOut.model_validate(r) for r in reviews]


@router.get("/tutor/{tutor_id}/summary", response_model=ReviewSummary)
async def tutor_review_summary(
    tutor_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ReviewSummary:
    avg, count = await crud.tutor_summary(db, tutor_id)
    return ReviewSummary(tutor_id=tutor_id, average_rating=avg, total_reviews=count)


@router.delete("/{review_id}", status_code=204, response_class=Response)
async def delete_review(
    review_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    review = await crud.get_review(db, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    is_staff = user.role in (Role.MODERATOR.value, Role.ADMIN.value, Role.SUPER_ADMIN.value)
    if review.author_id != uuid.UUID(user.id) and not is_staff:
        raise HTTPException(status_code=403, detail="Not allowed")
    await crud.delete_review(db, review)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------- Complaints ------------------------------

@router.post("/complaints", response_model=ComplaintOut, status_code=201)
async def file_complaint(
    payload: ComplaintCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComplaintOut:
    complaint = await crud.create_complaint(db, uuid.UUID(user.id), payload.model_dump())
    return ComplaintOut.model_validate(complaint)


@router.get("/complaints", response_model=list[ComplaintOut])
async def list_complaints(
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> list[ComplaintOut]:
    items = await crud.list_complaints(db, status_filter)
    return [ComplaintOut.model_validate(c) for c in items]


@router.post("/complaints/{complaint_id}/resolve", response_model=ComplaintOut)
async def resolve_complaint(
    complaint_id: uuid.UUID,
    payload: ComplaintResolve,
    _: CurrentUser = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> ComplaintOut:
    complaint = await crud.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    complaint.status = payload.status
    complaint.resolution = payload.resolution
    return ComplaintOut.model_validate(await crud.save(db, complaint))
