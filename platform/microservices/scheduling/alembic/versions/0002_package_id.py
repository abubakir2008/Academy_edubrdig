"""scheduling department: bookings.package_id (lesson-package redemptions)

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

SCHEMA = "scheduling"


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("bookings", "package_id", schema=SCHEMA)
