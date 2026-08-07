"""engagement department: dispute tickets + chat attachments

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

SCHEMA = "engagement"


def upgrade() -> None:
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

    op.add_column(
        "messages", sa.Column("attachment_url", sa.String(1024), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "messages", sa.Column("attachment_name", sa.String(255), nullable=True), schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_column("messages", "attachment_name", schema=SCHEMA)
    op.drop_column("messages", "attachment_url", schema=SCHEMA)
    op.drop_index("ix_tickets_kind", table_name="tickets", schema=SCHEMA)
    op.drop_column("tickets", "payment_id", schema=SCHEMA)
    op.drop_column("tickets", "kind", schema=SCHEMA)
