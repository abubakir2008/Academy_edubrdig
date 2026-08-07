"""content department: initial schema (ai logs, cms articles, localization)

Revision ID: 0001
Revises:
Create Date: 2026-07-30

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "content"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "ai_request_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature", sa.String(32), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_ai_request_logs_user_id", "ai_request_logs", ["user_id"], schema=SCHEMA)
    op.create_index("ix_ai_request_logs_feature", "ai_request_logs", ["feature"], schema=SCHEMA)

    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("type", sa.String(16), nullable=False, server_default="blog"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("seo_title", sa.String(255), nullable=True),
        sa.Column("seo_description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_articles_slug", "articles", ["slug"], unique=True, schema=SCHEMA)
    op.create_index("ix_articles_type", "articles", ["type"], schema=SCHEMA)
    op.create_index("ix_articles_published", "articles", ["published"], schema=SCHEMA)

    op.create_table(
        "languages",
        sa.Column("code", sa.String(8), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("locale", sa.String(8), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("locale", "key", name="uq_translations_locale_key"),
        schema=SCHEMA,
    )
    op.create_index("ix_translations_locale", "translations", ["locale"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("translations", schema=SCHEMA)
    op.drop_table("languages", schema=SCHEMA)
    op.drop_table("articles", schema=SCHEMA)
    op.drop_table("ai_request_logs", schema=SCHEMA)
