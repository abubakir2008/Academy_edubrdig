"""identity department: initial schema (users, profiles)

Revision ID: 0001
Revises:
Create Date: 2026-07-30

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "identity"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("oauth_provider", sa.String(32), nullable=True),
        sa.Column("oauth_subject", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_identity_users_email", "users", ["email"], unique=True, schema=SCHEMA)
    op.create_index("ix_identity_users_oauth_subject", "users", ["oauth_subject"], schema=SCHEMA)

    op.create_table(
        "profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("native_language", sa.String(32), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("bio", sa.String(2000), nullable=True),
        sa.Column(
            "languages", postgresql.ARRAY(sa.String(32)), nullable=False, server_default="{}"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("profiles", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)
