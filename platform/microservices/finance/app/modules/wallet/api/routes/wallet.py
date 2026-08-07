"""Wallet endpoints (namespaced under /wallet)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import Role

from ...crud import wallet as crud
from ...db.session import get_db
from ...models.wallet import WithdrawalStatus
from ...schemas.wallet import (
    CreditRequest,
    TransactionOut,
    WalletOut,
    WithdrawalOut,
    WithdrawalRequest,
)
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/wallet", tags=["wallet"])

require_finance = require_roles(Role.FINANCE_MANAGER, Role.ADMIN, Role.SUPER_ADMIN)


@router.get("/me", response_model=WalletOut)
async def my_wallet(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletOut:
    wallet = await crud.get_or_create(db, uuid.UUID(user.id))
    return WalletOut.model_validate(wallet)


@router.get("/me/transactions", response_model=list[TransactionOut])
async def my_transactions(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TransactionOut]:
    txs = await crud.list_transactions(db, uuid.UUID(user.id))
    return [TransactionOut.model_validate(t) for t in txs]


@router.post("/credit", response_model=TransactionOut, status_code=201)
async def credit_wallet(
    payload: CreditRequest,
    _: CurrentUser = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> TransactionOut:
    """Credit a tutor's wallet (called on successful payment / by finance staff)."""
    tx = await crud.credit(
        db, payload.tutor_id, payload.amount_cents, payload.reference, payload.description
    )
    return TransactionOut.model_validate(tx)


@router.post("/me/withdrawals", response_model=WithdrawalOut, status_code=201)
async def request_withdrawal(
    payload: WithdrawalRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalOut:
    wallet = await crud.get_or_create(db, uuid.UUID(user.id))
    if payload.amount_cents > wallet.balance_cents:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    wd = await crud.request_withdrawal(
        db, uuid.UUID(user.id), payload.amount_cents, payload.method, payload.destination
    )
    return WithdrawalOut.model_validate(wd)


@router.get("/me/withdrawals", response_model=list[WithdrawalOut])
async def my_withdrawals(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WithdrawalOut]:
    items = await crud.list_withdrawals(db, uuid.UUID(user.id))
    return [WithdrawalOut.model_validate(w) for w in items]


@router.get("/withdrawals", response_model=list[WithdrawalOut])
async def all_withdrawals(
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> list[WithdrawalOut]:
    items = await crud.list_all_withdrawals(db, status_filter)
    return [WithdrawalOut.model_validate(w) for w in items]


@router.post("/withdrawals/{wd_id}/approve", response_model=WithdrawalOut)
async def approve_withdrawal(
    wd_id: uuid.UUID,
    _: CurrentUser = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalOut:
    wd = await crud.get_withdrawal(db, wd_id)
    if wd is None:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if wd.status != WithdrawalStatus.REQUESTED.value:
        raise HTTPException(status_code=409, detail=f"Withdrawal already {wd.status}")
    wallet = await crud.get_or_create(db, wd.tutor_id)
    if wd.amount_cents > wallet.balance_cents:
        raise HTTPException(status_code=400, detail="Tutor balance insufficient")
    wd = await crud.approve_withdrawal(db, wd)
    return WithdrawalOut.model_validate(wd)


@router.post("/withdrawals/{wd_id}/reject", response_model=WithdrawalOut)
async def reject_withdrawal(
    wd_id: uuid.UUID,
    _: CurrentUser = Depends(require_finance),
    db: AsyncSession = Depends(get_db),
) -> WithdrawalOut:
    wd = await crud.get_withdrawal(db, wd_id)
    if wd is None:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    if wd.status != WithdrawalStatus.REQUESTED.value:
        raise HTTPException(status_code=409, detail=f"Withdrawal already {wd.status}")
    wd = await crud.reject_withdrawal(db, wd, note="Rejected by finance")
    return WithdrawalOut.model_validate(wd)
