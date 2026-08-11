"""backoffice department: add leads (public "leave a request" intake, restored
after the course-platform pivot dropped the old catalog/students department's
equivalent along with tutor search/matching)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-10

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SCHEMA = "backoffice"


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("goal", sa.String(255), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("study_place", sa.String(255), nullable=True),
        sa.Column("destination_country", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("contact_phone", sa.String(32), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_leads_status", "leads", ["status"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("leads", schema=SCHEMA)
