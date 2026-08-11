"""backoffice department: index leads.contact_phone / leads.contact_email

crud.find_recent_by_contact() looks these up on every POST /leads (the
platform's one public unauthenticated write) to catch double-submits and
repeat spam before writing another row.

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

SCHEMA = "backoffice"


def upgrade() -> None:
    op.create_index("ix_leads_contact_phone", "leads", ["contact_phone"], schema=SCHEMA)
    op.create_index("ix_leads_contact_email", "leads", ["contact_email"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_leads_contact_email", table_name="leads", schema=SCHEMA)
    op.drop_index("ix_leads_contact_phone", table_name="leads", schema=SCHEMA)
