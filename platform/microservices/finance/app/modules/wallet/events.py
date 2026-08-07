"""Event wiring for the Wallet Service (consumer).

Listens for successful payments and automatically credits the tutor's balance —
no request from the frontend is involved.
"""

from __future__ import annotations

import uuid

from edubridge_shared.events import Topics

from ...events import bus
from .crud import wallet as crud
from .db.session import SessionLocal


async def _on_payment_succeeded(data: dict, topic: str) -> None:
    payment_id = data.get("payment_id")
    async with SessionLocal() as db:
        # Idempotent: skip if this payment already credited the wallet.
        if payment_id and await crud.credit_exists(db, payment_id):
            return
        await crud.credit(
            db,
            uuid.UUID(data["tutor_id"]),
            int(data["tutor_earnings_cents"]),
            reference=payment_id,
            description="Lesson earnings",
        )


bus.on(Topics.PAYMENT_SUCCEEDED, _on_payment_succeeded)
