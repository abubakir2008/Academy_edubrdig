"""academics department: seed 100 tutor subject categories

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-12

"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SCHEMA = "academics"

# (name, slug) — a starter taxonomy for the public tutors page and course
# creation; staff can add/edit/remove any of these afterwards via the admin
# Categories CRUD, this just avoids launching with an empty list.
CATEGORIES: list[tuple[str, str]] = [
    ("Английский язык", "english"),
    ("Немецкий язык", "german"),
    ("Французский язык", "french"),
    ("Испанский язык", "spanish"),
    ("Китайский язык", "chinese"),
    ("Японский язык", "japanese"),
    ("Корейский язык", "korean"),
    ("Турецкий язык", "turkish"),
    ("Арабский язык", "arabic"),
    ("Итальянский язык", "italian"),
    ("Русский язык", "russian"),
    ("Кыргызский язык", "kyrgyz"),
    ("Русский как иностранный", "russian-as-foreign"),
    ("Польский язык", "polish"),
    ("Португальский язык", "portuguese"),
    ("Математика", "math"),
    ("Алгебра", "algebra"),
    ("Геометрия", "geometry"),
    ("Физика", "physics"),
    ("Химия", "chemistry"),
    ("Биология", "biology"),
    ("География", "geography"),
    ("История", "history"),
    ("Обществознание", "social-studies"),
    ("Литература", "literature"),
    ("Информатика", "computer-science"),
    ("Экономика", "economics"),
    ("Астрономия", "astronomy"),
    ("Черчение", "drafting"),
    ("Начальная школа", "elementary-school"),
    ("IELTS", "ielts"),
    ("TOEFL", "toefl"),
    ("SAT", "sat"),
    ("ОРТ", "ort"),
    ("ЕГЭ", "ege"),
    ("ОГЭ", "oge"),
    ("GMAT", "gmat"),
    ("GRE", "gre"),
    ("Кембриджские экзамены", "cambridge-exams"),
    ("DELF/DALF", "delf-dalf"),
    ("Программирование", "programming"),
    ("Python", "python"),
    ("JavaScript", "javascript"),
    ("Веб-разработка", "web-development"),
    ("Мобильная разработка", "mobile-development"),
    ("Data Science", "data-science"),
    ("Машинное обучение", "machine-learning"),
    ("Кибербезопасность", "cybersecurity"),
    ("Базы данных", "databases"),
    ("DevOps", "devops"),
    ("UI/UX дизайн", "ui-ux-design"),
    ("Тестирование ПО (QA)", "qa-testing"),
    ("1С программирование", "1c-programming"),
    ("Робототехника", "robotics"),
    ("Компьютерная грамотность", "computer-literacy"),
    ("Рисование", "drawing"),
    ("Живопись", "painting"),
    ("Графический дизайн", "graphic-design"),
    ("Фотография", "photography"),
    ("Видеомонтаж", "video-editing"),
    ("Анимация", "animation"),
    ("Игра на гитаре", "guitar"),
    ("Игра на фортепиано", "piano"),
    ("Игра на скрипке", "violin"),
    ("Вокал", "vocals"),
    ("Актёрское мастерство", "acting"),
    ("Танцы", "dance"),
    ("Театральное искусство", "theatre"),
    ("Каллиграфия", "calligraphy"),
    ("Кулинария", "cooking"),
    ("Бизнес и предпринимательство", "business"),
    ("Маркетинг", "marketing"),
    ("SMM", "smm"),
    ("Финансовая грамотность", "financial-literacy"),
    ("Бухгалтерский учёт", "accounting"),
    ("Публичные выступления", "public-speaking"),
    ("Менеджмент проектов", "project-management"),
    ("HR и рекрутинг", "hr-recruiting"),
    ("Копирайтинг", "copywriting"),
    ("Юриспруденция", "law"),
    ("Психология", "psychology"),
    ("Коучинг", "coaching"),
    ("Логистика", "logistics"),
    ("Продажи", "sales"),
    ("Аналитика данных", "data-analytics"),
    ("Шахматы", "chess"),
    ("Йога", "yoga"),
    ("Фитнес", "fitness"),
    ("Плавание", "swimming"),
    ("Единоборства", "martial-arts"),
    ("Вождение (теория ПДД)", "driving-theory"),
    ("Ораторское мастерство", "rhetoric"),
    ("Скорочтение", "speed-reading"),
    ("Подготовка к школе", "school-prep"),
    ("Раннее развитие", "early-development"),
    ("Медицина (подготовка к вузу)", "medicine-prep"),
    ("Инженерия", "engineering"),
    ("Архитектура", "architecture"),
    ("Экология", "ecology"),
    ("Предпринимательство для подростков", "teen-entrepreneurship"),
]


def upgrade() -> None:
    categories = sa.table(
        "categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        schema=SCHEMA,
    )
    op.bulk_insert(categories, [{"id": uuid.uuid4(), "name": name, "slug": slug} for name, slug in CATEGORIES])


def downgrade() -> None:
    slugs = [slug for _, slug in CATEGORIES]
    op.execute(
        sa.text(f'DELETE FROM {SCHEMA}.categories WHERE slug IN :slugs').bindparams(
            sa.bindparam("slugs", value=tuple(slugs), expanding=True)
        )
    )
