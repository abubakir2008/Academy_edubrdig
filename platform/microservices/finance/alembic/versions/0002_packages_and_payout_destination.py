"""finance department: lesson_packages table + withdrawals.destination

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-30

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "finance"


def upgrade() -> None:
    op.create_table(
        "lesson_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tutor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "payment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.payments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("total_lessons", sa.Integer(), nullable=False),
        sa.Column("lessons_remaining", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_lesson_packages_student_id", "lesson_packages", ["student_id"], schema=SCHEMA)
    op.create_index("ix_lesson_packages_tutor_id", "lesson_packages", ["tutor_id"], schema=SCHEMA)

    op.add_column(
        "withdrawals",
        sa.Column("destination", sa.String(255), nullable=True),
        schema=SCHEMA,
    )
    op.execute(f"ALTER TABLE {SCHEMA}.withdrawals ALTER COLUMN method SET DEFAULT 'bank_card'")


def downgrade() -> None:
    op.drop_column("withdrawals", "destination", schema=SCHEMA)
    op.drop_table("lesson_packages", schema=SCHEMA)
