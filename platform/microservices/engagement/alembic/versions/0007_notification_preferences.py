"""engagement department: notification_preferences table

Per-user push toggles (lesson reminders / chat messages / homework),
defaulting to all-on. See models/preference.py.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-01

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SCHEMA = "engagement"


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("lesson_reminders", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("chat_messages", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("homework", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("notification_preferences", schema=SCHEMA)
