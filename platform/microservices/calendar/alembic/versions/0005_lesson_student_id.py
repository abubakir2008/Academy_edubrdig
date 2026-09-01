"""calendar department: lessons.student_id (individual vs whole-group lessons)

Null means "the whole course roster" (the only option before this) — set,
it's a 1:1 lesson for that one student, invisible to the rest of the
roster. See routes/calendar.py's _authorize_participant/_lessons_for.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-01

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SCHEMA = "calendar"


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index("ix_lessons_student_id", "lessons", ["student_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_lessons_student_id", table_name="lessons", schema=SCHEMA)
    op.drop_column("lessons", "student_id", schema=SCHEMA)
