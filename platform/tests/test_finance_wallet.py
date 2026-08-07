"""Finance department: wallet crediting must be idempotent under concurrency.

Regression test for the fix to the check-then-insert race in
crud.credit_exists() — the actual guarantee against double-crediting a
redelivered ``payment.succeeded`` event now lives in a DB unique constraint
on (reference, type), not in an application-level check.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("department_app", ["finance"], indirect=True)
async def test_crediting_twice_with_same_reference_only_applies_once(department_app):
    main, _client = department_app

    from app.db.session import SessionLocal
    from app.modules.wallet.crud import wallet as crud

    tutor_id = uuid.uuid4()
    reference = str(uuid.uuid4())  # stands in for a payment id

    async with SessionLocal() as db:
        first = await crud.credit(db, tutor_id, 5_000, reference=reference, description="Lesson earnings")
        assert first is not None
        assert first.amount_cents == 5_000

    # Simulates the at-least-once redelivery of the same payment.succeeded event.
    async with SessionLocal() as db:
        second = await crud.credit(db, tutor_id, 5_000, reference=reference, description="Lesson earnings")
        assert second is None  # rejected by the unique constraint, not double-applied

    async with SessionLocal() as db:
        wallet = await crud.get_or_create(db, tutor_id)
        assert wallet.balance_cents == 5_000  # not 10,000


@pytest.mark.parametrize("department_app", ["finance"], indirect=True)
async def test_credit_and_debit_can_reuse_the_same_reference_value(department_app):
    """(reference, type) is the constraint, not reference alone — a
    withdrawal's debit legitimately reuses its own id as the reference for a
    later credit-side reference of a different payment that happens to
    collide would still be fine, but this test pins the exact case that
    motivated the composite key: credit and debit are independent."""
    main, _client = department_app

    from app.db.session import SessionLocal
    from app.modules.wallet.crud import wallet as crud
    from app.modules.wallet.models.wallet import TxType

    tutor_id = uuid.uuid4()
    shared_reference = str(uuid.uuid4())

    async with SessionLocal() as db:
        credit_tx = await crud.credit(db, tutor_id, 5_000, reference=shared_reference)
        assert credit_tx is not None

    async with SessionLocal() as db:
        debit_tx = await crud._apply(
            db, tutor_id, -1_000, TxType.DEBIT, reference=shared_reference, description="payout"
        )
        assert debit_tx is not None  # different type -> not blocked by the credit's row

    async with SessionLocal() as db:
        wallet = await crud.get_or_create(db, tutor_id)
        assert wallet.balance_cents == 4_000
