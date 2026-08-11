"""identity department: index on users.role

`GET /auth/admin/users?role=...` filters on this column, and it's called on
every course enrollment/teacher-assignment (academics' auto chat
provisioning looks up every super_admin by role).

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

SCHEMA = "identity"


def upgrade() -> None:
    op.create_index("ix_users_role", "users", ["role"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_users_role", table_name="users", schema=SCHEMA)
