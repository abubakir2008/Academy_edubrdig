"""calendar department: initial schema (lessons)

Revision ID: 0001
Revises:
Create Date: 2026-08-09

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "calendar"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_lessons_course_id", "lessons", ["course_id"], schema=SCHEMA)
    op.create_index("ix_lessons_teacher_id", "lessons", ["teacher_id"], schema=SCHEMA)
    op.create_index("ix_lessons_series_id", "lessons", ["series_id"], schema=SCHEMA)
    op.create_index("ix_lessons_scheduled_start", "lessons", ["scheduled_start"], schema=SCHEMA)
    op.create_index("ix_lessons_status", "lessons", ["status"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("lessons", schema=SCHEMA)
