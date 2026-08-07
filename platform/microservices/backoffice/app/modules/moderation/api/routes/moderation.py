"""Moderation endpoints (namespaced under /moderation)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.events import Topics
from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...db.session import get_db
from ...events import bus
from ...models.moderation import Document, ModStatus, VerificationRequest
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/moderation", tags=["moderation"])
require_moderator = require_roles(Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN)
require_tutor = require_roles(Role.TUTOR)


class VerificationIn(BaseModel):
    kind: str = Field(default="profile", pattern="^(profile|identity)$")


class DocumentIn(BaseModel):
    doc_type: str = Field(max_length=32)
    file_url: str = Field(max_length=1024)


class ReviewDecision(BaseModel):
    approve: bool
    note: str | None = None


class VerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tutor_id: uuid.UUID
    kind: str
    status: str
    note: str | None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tutor_id: uuid.UUID
    doc_type: str
    file_url: str
    status: str
    note: str | None


# ------------------------- Verification requests -----------------------

@router.post("/verification", response_model=VerificationOut, status_code=201)
async def submit_verification(
    payload: VerificationIn,
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> VerificationOut:
    req = VerificationRequest(tutor_id=uuid.UUID(user.id), kind=payload.kind)
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return VerificationOut.model_validate(req)


@router.get("/verification/me", response_model=list[VerificationOut])
async def my_verifications(
    user: CurrentUser = Depends(require_tutor), db: AsyncSession = Depends(get_db)
) -> list[VerificationOut]:
    """A tutor could submit and then never learn the outcome — moderators had
    a status view, tutors didn't."""
    stmt = (
        select(VerificationRequest)
        .where(VerificationRequest.tutor_id == uuid.UUID(user.id))
        .order_by(VerificationRequest.created_at.desc())
    )
    result = await db.execute(stmt)
    return [VerificationOut.model_validate(r) for r in result.scalars()]


@router.get("/verification", response_model=list[VerificationOut])
async def list_verifications(
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> list[VerificationOut]:
    stmt = select(VerificationRequest).order_by(VerificationRequest.created_at.desc())
    if status_filter:
        stmt = stmt.where(VerificationRequest.status == status_filter)
    result = await db.execute(stmt)
    return [VerificationOut.model_validate(r) for r in result.scalars()]


@router.post("/verification/{req_id}/review", response_model=VerificationOut)
async def review_verification(
    req_id: uuid.UUID,
    decision: ReviewDecision,
    moderator: CurrentUser = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> VerificationOut:
    req = await db.get(VerificationRequest, req_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    req.status = ModStatus.APPROVED.value if decision.approve else ModStatus.REJECTED.value
    req.note = decision.note
    req.reviewer_id = uuid.UUID(moderator.id)
    await db.commit()
    await db.refresh(req)
    if decision.approve:
        # Tutor service flips is_verified; search reindexes; tutor is notified.
        await bus.publish(
            Topics.TUTOR_VERIFIED,
            {"tutor_id": str(req.tutor_id), "kind": req.kind},
            key=str(req.tutor_id),
        )
    return VerificationOut.model_validate(req)


# ------------------------------ Documents ------------------------------

@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    payload: DocumentIn,
    user: CurrentUser = Depends(require_tutor),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    doc = Document(tutor_id=uuid.UUID(user.id), **payload.model_dump())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return DocumentOut.model_validate(doc)


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    tutor_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if tutor_id:
        stmt = stmt.where(Document.tutor_id == tutor_id)
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)
    result = await db.execute(stmt)
    return [DocumentOut.model_validate(d) for d in result.scalars()]


@router.post("/documents/{doc_id}/review", response_model=DocumentOut)
async def review_document(
    doc_id: uuid.UUID,
    decision: ReviewDecision,
    moderator: CurrentUser = Depends(require_moderator),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = ModStatus.APPROVED.value if decision.approve else ModStatus.REJECTED.value
    doc.note = decision.note
    doc.reviewer_id = uuid.UUID(moderator.id)
    await db.commit()
    await db.refresh(doc)
    return DocumentOut.model_validate(doc)
