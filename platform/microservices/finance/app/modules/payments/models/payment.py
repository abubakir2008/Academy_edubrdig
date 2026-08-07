"""Payment & refund models."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from edubridge_shared.database import TimestampMixin, UUIDMixin

from ..db.base import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    REFUNDED = "refunded"
    FAILED = "failed"


class Payment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "payments"

    student_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)  # total charged
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    commission_rate: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    commission_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    tutor_earnings_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), default=PaymentStatus.PENDING.value, nullable=False, index=True
    )
    gateway: Mapped[str] = mapped_column(String(32), default="mock", nullable=False)
    # Gateway's own payment/transaction id, for reconciling webhooks.
    provider_ref: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    refunds: Mapped[list["Refund"]] = relationship(
        back_populates="payment", cascade="all, delete-orphan", lazy="selectin"
    )


class LessonPackage(Base, UUIDMixin, TimestampMixin):
    """A prepaid bundle of lessons with one tutor, bought at a discount.

    Paid for and the tutor's earnings credited in full at purchase (via the
    same Payment row every single-lesson checkout uses, just with
    ``quantity=total_lessons``) — booking only decrements ``lessons_remaining``
    per lesson, it never triggers a second payment.
    """

    __tablename__ = "lesson_packages"

    student_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    tutor_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False, index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    total_lessons: Mapped[int] = mapped_column(Integer, nullable=False)
    lessons_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)


class Refund(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refunds"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="succeeded", nullable=False)

    payment: Mapped["Payment"] = relationship(back_populates="refunds")
