"""academics department: subject categories + category_id on courses

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "academics"


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True, schema=SCHEMA)

    op.add_column(
        "courses",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_courses_category_id",
        "courses",
        "categories",
        ["category_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )
    op.create_index("ix_courses_category_id", "courses", ["category_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_courses_category_id", table_name="courses", schema=SCHEMA)
    op.drop_constraint("fk_courses_category_id", "courses", schema=SCHEMA, type_="foreignkey")
    op.drop_column("courses", "category_id", schema=SCHEMA)
    op.drop_table("categories", schema=SCHEMA)
