"""catalog department: initial schema (tutors, students, favorites, progress)

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

SCHEMA = "catalog"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    # Full-text search relies on this Postgres feature; it's on by default from
    # PG 9.1+, but stating it explicitly documents the dependency.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "tutors",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("headline", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(1024), nullable=True),
        sa.Column("photo_url", sa.String(1024), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("native_language", sa.String(32), nullable=True),
        sa.Column("languages_taught", postgresql.ARRAY(sa.String(32)), nullable=False, server_default="{}"),
        sa.Column("specializations", postgresql.ARRAY(sa.String(64)), nullable=False, server_default="{}"),
        sa.Column("experience_years", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trial_price_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rating", sa.Numeric(3, 2), nullable=False, server_default="0"),
        sa.Column("total_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_lessons", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('simple', coalesce(headline, '')), 'A') || "
                "setweight(to_tsvector('simple', coalesce(description, '')), 'B')",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tutors_search_vector", "tutors", ["search_vector"], schema=SCHEMA, postgresql_using="gin"
    )

    op.create_table(
        "working_hours",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tutor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tutors.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_working_hours_tutor_id", "working_hours", ["tutor_id"], schema=SCHEMA)

    op.create_table(
        "certificates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tutor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tutors.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("issued_by", sa.String(255), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("file_url", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_certificates_tutor_id", "certificates", ["tutor_id"], schema=SCHEMA)

    op.create_table(
        "students",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learning_goals", sa.Text(), nullable=True),
        sa.Column("learning_languages", postgresql.ARRAY(sa.String(32)), nullable=False, server_default="{}"),
        sa.Column("level", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "favorite_tutors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.students.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tutor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "tutor_id", name="uq_favorite_tutors_student_id"),
        schema=SCHEMA,
    )
    op.create_index("ix_favorite_tutors_student_id", "favorite_tutors", ["student_id"], schema=SCHEMA)

    op.create_table(
        "learning_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.students.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(64), nullable=False),
        sa.Column("lessons_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hours_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_learning_progress_student_id", "learning_progress", ["student_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("learning_progress", schema=SCHEMA)
    op.drop_table("favorite_tutors", schema=SCHEMA)
    op.drop_table("students", schema=SCHEMA)
    op.drop_table("certificates", schema=SCHEMA)
    op.drop_table("working_hours", schema=SCHEMA)
    op.drop_table("tutors", schema=SCHEMA)
