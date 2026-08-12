"""backoffice department: preferred_tutor_id on leads

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-12

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SCHEMA = "backoffice"


def upgrade() -> None:
    op.add_column(
        "leads", sa.Column("preferred_tutor_id", postgresql.UUID(as_uuid=True), nullable=True), schema=SCHEMA
    )
    op.create_index("ix_leads_preferred_tutor_id", "leads", ["preferred_tutor_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_leads_preferred_tutor_id", table_name="leads", schema=SCHEMA)
    op.drop_column("leads", "preferred_tutor_id", schema=SCHEMA)
