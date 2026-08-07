"""catalog department: add student_leads (onboarding intake form)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-07

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "catalog"


def upgrade() -> None:
    op.create_table(
        "student_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject", sa.String(64), nullable=True),
        sa.Column("goal", sa.String(64), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("study_place", sa.String(255), nullable=True),
        sa.Column("destination_country", sa.String(64), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("contact_phone", sa.String(32), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_student_leads_created_at", "student_leads", ["created_at"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("student_leads", schema=SCHEMA)
