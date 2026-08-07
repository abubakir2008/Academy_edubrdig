"""Payment persistence + commission calculation."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.payment import LessonPackage, Payment, PaymentStatus, Refund

#: lesson_count -> discount fraction off the tutor's per-lesson price.
PACKAGE_DISCOUNTS: dict[int, float] = {5: 0.08, 10: 0.15, 20: 0.20, 40: 0.25}


def split_amount(total_cents: int, rate: float) -> tuple[int, int]:
    """Return ``(commission_cents, tutor_earnings_cents)``."""
    commission = round(total_cents * rate)
    return commission, total_cents - commission


def package_price(per_lesson_cents: int, lesson_count: int) -> int:
    """Total price for a package, after its tier discount."""
    tier = max((n for n in PACKAGE_DISCOUNTS if n <= lesson_count), default=1)
    discount = PACKAGE_DISCOUNTS.get(tier, 0.0)
    return round(per_lesson_cents * lesson_count * (1 - discount))


async def create_payment(
    db: AsyncSession,
    *,
    student_id: uuid.UUID,
    tutor_id: uuid.UUID,
    booking_id: uuid.UUID | None,
    total_cents: int,
    currency: str,
    rate: float,
    gateway: str,
    quantity: int = 1,
    status: str = PaymentStatus.PENDING.value,
) -> Payment:
    commission, earnings = split_amount(total_cents, rate)
    payment = Payment(
        student_id=student_id,
        tutor_id=tutor_id,
        booking_id=booking_id,
        quantity=quantity,
        amount_cents=total_cents,
        currency=currency,
        commission_rate=rate,
        commission_cents=commission,
        tutor_earnings_cents=earnings,
        gateway=gateway,
        status=status,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def create_package(
    db: AsyncSession,
    *,
    student_id: uuid.UUID,
    tutor_id: uuid.UUID,
    payment_id: uuid.UUID,
    total_lessons: int,
    price_cents: int,
    currency: str,
) -> LessonPackage:
    package = LessonPackage(
        student_id=student_id,
        tutor_id=tutor_id,
        payment_id=payment_id,
        total_lessons=total_lessons,
        lessons_remaining=total_lessons,
        price_cents=price_cents,
        currency=currency,
    )
    db.add(package)
    await db.commit()
    await db.refresh(package)
    return package


async def list_packages_for_student(db: AsyncSession, student_id: uuid.UUID) -> list[LessonPackage]:
    result = await db.execute(
        select(LessonPackage)
        .where(LessonPackage.student_id == student_id, LessonPackage.lessons_remaining > 0)
        .order_by(LessonPackage.created_at.desc())
    )
    return list(result.scalars().all())


async def get_package(db: AsyncSession, package_id: uuid.UUID) -> LessonPackage | None:
    return await db.get(LessonPackage, package_id)


async def consume_package_lesson(db: AsyncSession, package: LessonPackage) -> LessonPackage:
    package.lessons_remaining -= 1
    await db.commit()
    await db.refresh(package)
    return package


async def get_by_provider_ref(db: AsyncSession, provider_ref: str) -> Payment | None:
    result = await db.execute(select(Payment).where(Payment.provider_ref == provider_ref))
    return result.scalar_one_or_none()


async def mark_succeeded(db: AsyncSession, payment: Payment) -> bool:
    """Idempotent: returns True only on the transition into SUCCEEDED."""
    if payment.status == PaymentStatus.SUCCEEDED.value:
        return False
    payment.status = PaymentStatus.SUCCEEDED.value
    await db.commit()
    await db.refresh(payment)
    return True


async def set_provider_ref(db: AsyncSession, payment: Payment, ref: str) -> Payment:
    payment.provider_ref = ref
    await db.commit()
    await db.refresh(payment)
    return payment


async def get(db: AsyncSession, payment_id: uuid.UUID) -> Payment | None:
    return await db.get(Payment, payment_id)


async def list_for_user(db: AsyncSession, user_id: uuid.UUID, as_role: str) -> list[Payment]:
    col = Payment.tutor_id if as_role == "tutor" else Payment.student_id
    result = await db.execute(
        select(Payment).where(col == user_id).order_by(Payment.created_at.desc())
    )
    return list(result.scalars().unique().all())


async def refunded_total(payment: Payment) -> int:
    return sum(r.amount_cents for r in payment.refunds)


async def add_refund(db: AsyncSession, payment: Payment, amount_cents: int, reason: str | None) -> Refund:
    refund = Refund(payment_id=payment.id, amount_cents=amount_cents, reason=reason)
    db.add(refund)
    if amount_cents >= payment.amount_cents - await refunded_total(payment):
        payment.status = PaymentStatus.REFUNDED.value
    await db.commit()
    await db.refresh(refund)
    return refund
