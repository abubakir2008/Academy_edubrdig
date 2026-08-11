"""identity department: drop profile contact/locale fields (country, timezone,
native_language, phone, bio, languages) — unused, removed to avoid confusion
for future frontend work; only full_name/avatar_url remain on profiles.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-09

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SCHEMA = "identity"


def upgrade() -> None:
    op.drop_column("profiles", "languages", schema=SCHEMA)
    op.drop_column("profiles", "bio", schema=SCHEMA)
    op.drop_column("profiles", "phone", schema=SCHEMA)
    op.drop_column("profiles", "native_language", schema=SCHEMA)
    op.drop_column("profiles", "timezone", schema=SCHEMA)
    op.drop_column("profiles", "country", schema=SCHEMA)


def downgrade() -> None:
    op.add_column("profiles", sa.Column("country", sa.String(2), nullable=True), schema=SCHEMA)
    op.add_column("profiles", sa.Column("timezone", sa.String(64), nullable=True), schema=SCHEMA)
    op.add_column("profiles", sa.Column("native_language", sa.String(32), nullable=True), schema=SCHEMA)
    op.add_column("profiles", sa.Column("phone", sa.String(32), nullable=True), schema=SCHEMA)
    op.add_column("profiles", sa.Column("bio", sa.String(2000), nullable=True), schema=SCHEMA)
    op.add_column(
        "profiles",
        sa.Column("languages", postgresql.ARRAY(sa.String(32)), nullable=False, server_default="{}"),
        schema=SCHEMA,
    )
