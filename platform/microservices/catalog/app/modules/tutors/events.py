"""Event wiring for the Tutors module (consumer only).

- Consumes ``review.created`` to refresh the denormalised rating.
- Consumes ``tutor.verified`` to flip ``is_verified``.

There used to be a ``tutor.updated`` publish here so the Search service could
reindex ElasticSearch. Search now queries this module's own table directly
(same department, same database — see ``modules/search``), so a tutor row
update *is* the search update; nothing downstream needs to be told.
"""

from __future__ import annotations

import uuid

from edubridge_shared.events import Topics

from ...events import bus
from .crud import tutor as crud
from .db.session import SessionLocal


async def _on_review_created(data: dict, topic: str) -> None:
    async with SessionLocal() as db:
        tutor = await crud.get(db, uuid.UUID(data["tutor_id"]))
        if tutor is None:
            return
        tutor.rating = data["average_rating"]
        tutor.total_reviews = int(data["total_reviews"])
        await crud.update(db, tutor, {})


async def _on_tutor_verified(data: dict, topic: str) -> None:
    async with SessionLocal() as db:
        tutor = await crud.get_or_create(db, uuid.UUID(data["tutor_id"]))
        tutor.is_verified = True
        await crud.update(db, tutor, {})


bus.on(Topics.REVIEW_CREATED, _on_review_created)
bus.on(Topics.TUTOR_VERIFIED, _on_tutor_verified)
