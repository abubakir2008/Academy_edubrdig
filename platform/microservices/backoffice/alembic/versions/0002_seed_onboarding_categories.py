"""backoffice department: seed onboarding reference lists (universities, goals)

The onboarding intake form (catalog department, /students/leads) reads its
"where do you study" and "why" option lists from here — GET /admin/categories
is public, so the form can fetch them without auth, and staff can edit the
lists later from /dashboard/admin without a deploy.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-07

"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SCHEMA = "backoffice"

# Starting set of well-known Bishkek universities — not an authoritative
# "top 30", just a usable seed. Editable from /dashboard/admin afterwards.
UNIVERSITIES = [
    "Кыргызский национальный университет им. Ж. Баласагына",
    "Кыргызско-Российский Славянский университет им. Б. Ельцина (КРСУ)",
    "Американский университет в Центральной Азии (АУЦА)",
    "Кыргызский государственный технический университет им. И. Раззакова (КГТУ)",
    "Кыргызский национальный аграрный университет им. К.И. Скрябина",
    "Кыргызский государственный университет им. И. Арабаева",
    "Бишкекский государственный университет им. К. Карасаева",
    "Кыргызско-Турецкий университет «Манас»",
    "Международный университет Кыргызстана (МУК)",
    "Международный университет Ала-Тоо",
    "Международный Кувейтский университет",
    "Кыргызский экономический университет им. М. Рыскулбекова",
    "Кыргызская государственная медицинская академия им. И.К. Ахунбаева (КГМА)",
    "Кыргызская государственная юридическая академия",
    "Кыргызский государственный университет строительства, транспорта и архитектуры им. Н. Исанова (КГУСТА)",
    "Исламский университет Кыргызстана",
    "Salymbekov University",
    "International School of Medicine (ISM)",
    "Кыргызско-Узбекский международный университет",
    "Бишкекская финансово-экономическая академия",
    "Кыргызская государственная академия физической культуры и спорта",
    "Академия МВД Кыргызской Республики",
    "Международная академия управления, права, финансов и бизнеса",
    "Университет Адам (Adam University)",
]

GOALS = [
    ("goal-personal", "Для себя"),
    ("goal-toefl", "TOEFL"),
    ("goal-ielts", "IELTS"),
    ("goal-study", "Учёба и школа"),
    ("goal-career", "Работа и карьера"),
    ("goal-other", "Другое"),
]

categories = sa.table(
    "categories",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("slug", sa.String),
    sa.column("name", sa.String),
    sa.column("group", sa.String),
    schema=SCHEMA,
)


def upgrade() -> None:
    rows = [
        {"id": uuid.uuid4(), "slug": f"university-{i:02d}", "name": name, "group": "university"}
        for i, name in enumerate(UNIVERSITIES, start=1)
    ] + [
        {"id": uuid.uuid4(), "slug": slug, "name": name, "group": "goal"}
        for slug, name in GOALS
    ]
    op.bulk_insert(categories, rows)


def downgrade() -> None:
    op.execute(f"DELETE FROM {SCHEMA}.categories WHERE \"group\" IN ('university', 'goal')")
