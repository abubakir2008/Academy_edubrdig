"""calendar department: Zoom integration (per-tutor OAuth accounts + meeting fields on lessons)

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-09

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "calendar"


def upgrade() -> None:
    op.create_table(
        "zoom_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tutor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("zoom_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_zoom_accounts_tutor_id", "zoom_accounts", ["tutor_id"], unique=True, schema=SCHEMA
    )

    op.add_column("lessons", sa.Column("zoom_meeting_id", sa.String(32), nullable=True), schema=SCHEMA)
    op.add_column("lessons", sa.Column("meeting_url", sa.String(512), nullable=True), schema=SCHEMA)
    op.add_column("lessons", sa.Column("start_url", sa.String(512), nullable=True), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column("lessons", "start_url", schema=SCHEMA)
    op.drop_column("lessons", "meeting_url", schema=SCHEMA)
    op.drop_column("lessons", "zoom_meeting_id", schema=SCHEMA)
    op.drop_table("zoom_accounts", schema=SCHEMA)
