"""calendar department: homework table

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-01

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SCHEMA = "calendar"


def upgrade() -> None:
    op.create_table(
        "homework",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lesson_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="assigned"),
        sa.Column("submission_url", sa.String(500), nullable=True),
        sa.Column("submission_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grade", sa.Float(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_homework_lesson_id", "homework", ["lesson_id"], schema=SCHEMA)
    op.create_index("ix_homework_course_id", "homework", ["course_id"], schema=SCHEMA)
    op.create_index("ix_homework_teacher_id", "homework", ["teacher_id"], schema=SCHEMA)
    op.create_index("ix_homework_student_id", "homework", ["student_id"], schema=SCHEMA)
    op.create_index("ix_homework_status", "homework", ["status"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("homework", schema=SCHEMA)
