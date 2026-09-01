"""engagement department: push_tokens table

Backs the mobile app's push notifications — one row per device that has ever
registered an Expo push token, keyed by the token itself (see the model's
docstring for why).

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-28

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SCHEMA = "engagement"


def upgrade() -> None:
    op.create_table(
        "push_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("token", name="uq_push_tokens_token"),
        schema=SCHEMA,
    )
    op.create_index("ix_push_tokens_user_id", "push_tokens", ["user_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("push_tokens", schema=SCHEMA)
