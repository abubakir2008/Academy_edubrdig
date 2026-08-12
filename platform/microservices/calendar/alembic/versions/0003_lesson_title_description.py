"""calendar department: title + description on lessons

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-12

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SCHEMA = "calendar"


def upgrade() -> None:
    op.add_column("lessons", sa.Column("title", sa.String(200), nullable=True), schema=SCHEMA)
    op.add_column("lessons", sa.Column("description", sa.Text(), nullable=True), schema=SCHEMA)


def downgrade() -> None:
    op.drop_column("lessons", "description", schema=SCHEMA)
    op.drop_column("lessons", "title", schema=SCHEMA)
