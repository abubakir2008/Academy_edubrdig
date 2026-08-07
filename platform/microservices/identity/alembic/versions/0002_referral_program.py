"""identity department: referral_code + referred_by_id on users

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-30

"""
from __future__ import annotations

import secrets

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "identity"
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # matches crud/user.py::_new_referral_code


def _new_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(8))


def upgrade() -> None:
    op.add_column("users", sa.Column("referral_code", sa.String(16), nullable=True), schema=SCHEMA)
    op.add_column(
        "users",
        sa.Column("referred_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )

    # Backfill existing rows (this table predates the column, so it can't just
    # get a single shared server_default) with unique codes, then enforce
    # NOT NULL + UNIQUE the same as any user created from now on.
    bind = op.get_bind()
    user_ids = [row[0] for row in bind.execute(sa.text(f"SELECT id FROM {SCHEMA}.users")).fetchall()]
    seen: set[str] = set()
    for user_id in user_ids:
        code = _new_code()
        while code in seen:
            code = _new_code()
        seen.add(code)
        bind.execute(
            sa.text(f"UPDATE {SCHEMA}.users SET referral_code = :code WHERE id = :id"),
            {"code": code, "id": user_id},
        )

    op.alter_column("users", "referral_code", nullable=False, schema=SCHEMA)
    op.create_unique_constraint("uq_users_referral_code", "users", ["referral_code"], schema=SCHEMA)
    op.create_index("ix_users_referral_code", "users", ["referral_code"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_users_referral_code", table_name="users", schema=SCHEMA)
    op.drop_constraint("uq_users_referral_code", "users", schema=SCHEMA, type_="unique")
    op.drop_column("users", "referred_by_id", schema=SCHEMA)
    op.drop_column("users", "referral_code", schema=SCHEMA)
