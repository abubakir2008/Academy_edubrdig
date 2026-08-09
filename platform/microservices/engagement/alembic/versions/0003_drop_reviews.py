"""engagement department: drop reviews + complaints (tutor/lesson rating feature removed)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-08

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SCHEMA = "engagement"


def upgrade() -> None:
    op.drop_table("complaints", schema=SCHEMA)
    op.drop_table("reviews", schema=SCHEMA)


def downgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tutor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("author_id", "lesson_id", name="uq_reviews_author_lesson"),
        schema=SCHEMA,
    )
    op.create_index("ix_reviews_author_id", "reviews", ["author_id"], schema=SCHEMA)
    op.create_index("ix_reviews_tutor_id", "reviews", ["tutor_id"], schema=SCHEMA)
    op.create_index("ix_reviews_lesson_id", "reviews", ["lesson_id"], schema=SCHEMA)

    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_complaints_author_id", "complaints", ["author_id"], schema=SCHEMA)
    op.create_index("ix_complaints_status", "complaints", ["status"], schema=SCHEMA)
