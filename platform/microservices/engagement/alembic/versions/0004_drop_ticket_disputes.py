"""engagement department: drop ticket dispute/refund fields (finance department removed)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-08

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SCHEMA = "engagement"


def upgrade() -> None:
    op.drop_index("ix_tickets_kind", table_name="tickets", schema=SCHEMA)
    op.drop_column("tickets", "payment_id", schema=SCHEMA)
    op.drop_column("tickets", "kind", schema=SCHEMA)


def downgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("kind", sa.String(16), nullable=False, server_default="general"),
        schema=SCHEMA,
    )
    op.add_column(
        "tickets",
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index("ix_tickets_kind", "tickets", ["kind"], schema=SCHEMA)
