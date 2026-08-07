"""Wallet, transactions and withdrawals for tutors."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class TxType(str, enum.Enum):
    CREDIT = "credit"        # lesson earnings credited
    DEBIT = "debit"          # withdrawal deducted
    REFUND = "refund"        # earnings reversed on refund
    ADJUSTMENT = "adjustment"


class WithdrawalStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class Wallet(Base, TimestampMixin):
    __tablename__ = "wallets"

    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    balance_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)


class WalletTransaction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wallet_transactions"
    __table_args__ = (
        # Makes crediting idempotent under concurrency: the application-level
        # "does a transaction for this reference exist?" check in
        # crud.credit_exists() is a check-then-insert race on its own, so the
        # actual guarantee against double-crediting a redelivered
        # payment.succeeded event has to live here. (reference, type) rather
        # than reference alone because the same UUID is reused as the
        # reference for a withdrawal's debit — see crud.approve_withdrawal().
        Index(
            "ix_wallet_transactions_reference_type",
            "reference",
            "type",
            unique=True,
            postgresql_where=text("reference IS NOT NULL"),
        ),
    )

    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)  # signed
    balance_after_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Withdrawal(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "withdrawals"

    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    method: Mapped[str] = mapped_column(String(32), default="bank_card", nullable=False)
    # Free-text account/card/wallet identifier for that method (masked by the
    # frontend before display — this table is the source of truth for payout,
    # not a UI concern).
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=WithdrawalStatus.REQUESTED.value, nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
