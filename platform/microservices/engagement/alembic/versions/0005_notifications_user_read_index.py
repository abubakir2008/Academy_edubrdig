"""engagement department: composite index on notifications(user_id, read)

list_for_user/unread_count/mark_all_read all filter on this pair together;
the existing single-column index on user_id doesn't serve that combined
filter as well as a composite does.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-11

"""
from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SCHEMA = "engagement"


def upgrade() -> None:
    op.create_index(
        "ix_notifications_user_id_read", "notifications", ["user_id", "read"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id_read", table_name="notifications", schema=SCHEMA)
