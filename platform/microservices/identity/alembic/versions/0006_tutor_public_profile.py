"""identity department: public tutor-profile fields on profiles

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

SCHEMA = "identity"


def upgrade() -> None:
    op.add_column("profiles", sa.Column("experience_years", sa.Integer(), nullable=True), schema=SCHEMA)
    op.add_column("profiles", sa.Column("bio_short", sa.String(280), nullable=True), schema=SCHEMA)
    op.add_column("profiles", sa.Column("bio_full", sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column(
        "profiles", sa.Column("languages", postgresql.ARRAY(sa.String(64)), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "profiles",
        sa.Column("category_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("profiles", "category_ids", schema=SCHEMA)
    op.drop_column("profiles", "languages", schema=SCHEMA)
    op.drop_column("profiles", "bio_full", schema=SCHEMA)
    op.drop_column("profiles", "bio_short", schema=SCHEMA)
    op.drop_column("profiles", "experience_years", schema=SCHEMA)
