"""Wallet persistence + balance mutations."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.wallet import (
    TxType,
    Wallet,
    WalletTransaction,
    Withdrawal,
    WithdrawalStatus,
)


async def get_or_create(db: AsyncSession, tutor_id: uuid.UUID) -> Wallet:
    wallet = await db.get(Wallet, tutor_id)
    if wallet is None:
        wallet = Wallet(tutor_id=tutor_id, balance_cents=0)
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
    return wallet


async def _apply(
    db: AsyncSession,
    tutor_id: uuid.UUID,
    delta_cents: int,
    tx_type: TxType,
    reference: str | None,
    description: str | None,
) -> WalletTransaction | None:
    """Returns None (instead of raising) if this (reference, type) already
    posted — the database's unique constraint is the actual idempotency
    guarantee (see the model); ``credit_exists`` is only a fast-path that
    avoids hitting it in the common case.
    """
    wallet = await get_or_create(db, tutor_id)
    wallet.balance_cents += delta_cents
    tx = WalletTransaction(
        tutor_id=tutor_id,
        type=tx_type.value,
        amount_cents=delta_cents,
        balance_after_cents=wallet.balance_cents,
        reference=reference,
        description=description,
    )
    db.add(tx)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return None
    await db.refresh(tx)
    return tx


async def credit(
    db, tutor_id, amount_cents, reference=None, description=None
) -> WalletTransaction | None:
    return await _apply(db, tutor_id, amount_cents, TxType.CREDIT, reference, description)


async def credit_exists(db: AsyncSession, reference: str) -> bool:
    """True if a credit for this reference (payment id) was already applied.

    Makes event handling idempotent so an at-least-once redelivered
    ``payment.succeeded`` cannot double-credit the tutor.
    """
    result = await db.execute(
        select(WalletTransaction.id).where(
            WalletTransaction.reference == reference,
            WalletTransaction.type == TxType.CREDIT.value,
        ).limit(1)
    )
    return result.first() is not None


async def list_transactions(db: AsyncSession, tutor_id: uuid.UUID) -> list[WalletTransaction]:
    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.tutor_id == tutor_id)
        .order_by(WalletTransaction.created_at.desc())
    )
    return list(result.scalars().all())


async def request_withdrawal(
    db: AsyncSession, tutor_id: uuid.UUID, amount_cents: int, method: str, destination: str
) -> Withdrawal:
    wd = Withdrawal(tutor_id=tutor_id, amount_cents=amount_cents, method=method, destination=destination)
    db.add(wd)
    await db.commit()
    await db.refresh(wd)
    return wd


async def get_withdrawal(db: AsyncSession, wd_id: uuid.UUID) -> Withdrawal | None:
    return await db.get(Withdrawal, wd_id)


async def list_withdrawals(db: AsyncSession, tutor_id: uuid.UUID) -> list[Withdrawal]:
    result = await db.execute(
        select(Withdrawal)
        .where(Withdrawal.tutor_id == tutor_id)
        .order_by(Withdrawal.created_at.desc())
    )
    return list(result.scalars().all())


async def list_all_withdrawals(db: AsyncSession, status: str | None) -> list[Withdrawal]:
    """Finance staff need every tutor's requests, not just one — there was no
    way to even see a withdrawal id to approve/reject before this."""
    stmt = select(Withdrawal).order_by(Withdrawal.created_at.desc())
    if status:
        stmt = stmt.where(Withdrawal.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def approve_withdrawal(db: AsyncSession, wd: Withdrawal) -> Withdrawal:
    """Deduct balance and mark the withdrawal paid."""
    wd.status = WithdrawalStatus.PAID.value
    await _apply(
        db, wd.tutor_id, -wd.amount_cents, TxType.DEBIT,
        reference=str(wd.id), description="Withdrawal payout",
    )
    await db.refresh(wd)
    return wd


async def reject_withdrawal(db: AsyncSession, wd: Withdrawal, note: str | None) -> Withdrawal:
    wd.status = WithdrawalStatus.REJECTED.value
    wd.note = note
    await db.commit()
    await db.refresh(wd)
    return wd
