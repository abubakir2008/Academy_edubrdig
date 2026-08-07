"""finance department: initial schema (payments, refunds, wallets, transactions, withdrawals)

Revision ID: 0001
Revises:
Create Date: 2026-07-30

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "finance"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tutor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("commission_rate", sa.Numeric(4, 3), nullable=False),
        sa.Column("commission_cents", sa.Integer(), nullable=False),
        sa.Column("tutor_earnings_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("gateway", sa.String(32), nullable=False, server_default="mock"),
        sa.Column("provider_ref", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_payments_student_id", "payments", ["student_id"], schema=SCHEMA)
    op.create_index("ix_payments_tutor_id", "payments", ["tutor_id"], schema=SCHEMA)
    op.create_index("ix_payments_status", "payments", ["status"], schema=SCHEMA)
    op.create_index("ix_payments_provider_ref", "payments", ["provider_ref"], schema=SCHEMA)

    op.create_table(
        "refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "payment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="succeeded"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"], schema=SCHEMA)

    op.create_table(
        "wallets",
        sa.Column("tutor_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("balance_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tutor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("balance_after_cents", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(128), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_wallet_transactions_tutor_id", "wallet_transactions", ["tutor_id"], schema=SCHEMA)
    # payment.succeeded is redelivered at least once; this constraint is what
    # actually makes wallet crediting idempotent under concurrency — the
    # application-level "does a credit for this reference exist?" check in
    # credit_exists() has a check-then-insert race, so the guarantee has to
    # live here, in the database. (reference, type) rather than reference
    # alone because the same UUID string is reused as the reference for a
    # withdrawal's debit — see approve_withdrawal().
    op.create_index(
        "ix_wallet_transactions_reference_type",
        "wallet_transactions",
        ["reference", "type"],
        schema=SCHEMA,
        unique=True,
        postgresql_where=sa.text("reference IS NOT NULL"),
    )

    op.create_table(
        "withdrawals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tutor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("method", sa.String(32), nullable=False, server_default="bank"),
        sa.Column("status", sa.String(16), nullable=False, server_default="requested"),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_withdrawals_tutor_id", "withdrawals", ["tutor_id"], schema=SCHEMA)
    op.create_index("ix_withdrawals_status", "withdrawals", ["status"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("withdrawals", schema=SCHEMA)
    op.drop_table("wallet_transactions", schema=SCHEMA)
    op.drop_table("wallets", schema=SCHEMA)
    op.drop_table("refunds", schema=SCHEMA)
    op.drop_table("payments", schema=SCHEMA)
