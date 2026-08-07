"""Payment endpoints (namespaced under /payments)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.clients import ServiceClient, ServiceError, service_url
from edubridge_shared.events import Topics
from edubridge_shared.fastapi_auth import CurrentUser

from ....wallet.crud import wallet as wallet_crud
from ...core.config import get_settings
from ...crud import payment as crud
from ...db.session import get_db
from ...events import bus
from ...models.payment import Payment
from ...providers import get_provider
from ...schemas.payment import (
    CheckoutRequest,
    CheckoutResponse,
    LessonPackageOut,
    PackageCheckoutRequest,
    PaymentOut,
    Receipt,
    RefundOut,
    RefundRequest,
)
from ..deps import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])
_settings = get_settings()
_booking = ServiceClient(service_url("booking"))
_tutors = ServiceClient(service_url("tutors"))
_identity = ServiceClient(service_url("auth"))

REFERRAL_BONUS_CENTS = 500  # flat $5-equivalent, credited once per referred student


async def _publish_succeeded(payment: Payment) -> None:
    """Fan out: wallet credits the tutor, notifications + analytics react."""
    await bus.publish(
        Topics.PAYMENT_SUCCEEDED,
        {
            "payment_id": str(payment.id),
            "student_id": str(payment.student_id),
            "tutor_id": str(payment.tutor_id),
            "amount_cents": payment.amount_cents,
            "tutor_earnings_cents": payment.tutor_earnings_cents,
            "commission_cents": payment.commission_cents,
            "currency": payment.currency,
            "quantity": payment.quantity,
        },
        key=str(payment.tutor_id),
    )


async def _maybe_reward_referral(db: AsyncSession, payment: Payment) -> None:
    """One-time bonus to whoever referred this student, on their first
    successful payment (not every payment — otherwise a single active
    referral would pay out forever)."""
    prior = await crud.list_for_user(db, payment.student_id, "student")
    succeeded_count = sum(1 for p in prior if p.status == "succeeded")
    if succeeded_count != 1:  # this payment itself is already in `prior`
        return
    try:
        info = await _identity.get(f"/auth/internal/referrer/{payment.student_id}")
    except ServiceError:
        return
    referrer_id = info.get("referrer_id")
    if not referrer_id:
        return
    await wallet_crud.credit(
        db,
        uuid.UUID(referrer_id),
        REFERRAL_BONUS_CENTS,
        reference=f"referral:{payment.student_id}",
        description="Referral bonus — invited student's first lesson",
    )


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: CheckoutRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Start payment for a booking. Amount/tutor come from the booking, not the client."""
    token = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    try:
        booking = await _booking.get(f"/booking/{payload.booking_id}", token=token)
    except ServiceError as exc:
        if exc.status == 404:
            raise HTTPException(status_code=404, detail="Booking not found") from exc
        raise HTTPException(status_code=502, detail="Could not load booking") from exc

    if booking["student_id"] != user.id:
        raise HTTPException(status_code=403, detail="You can only pay for your own booking")

    provider = get_provider()
    payment = await crud.create_payment(
        db,
        student_id=uuid.UUID(user.id),
        tutor_id=uuid.UUID(booking["tutor_id"]),
        booking_id=uuid.UUID(booking["id"]),
        total_cents=int(booking["price_cents"]),
        currency=booking.get("currency", "USD"),
        rate=_settings.commission_rate,
        gateway=provider.name,
    )

    init = await provider.create(
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        order_id=str(payment.id),
        description=f"Lesson with tutor {payment.tutor_id}",
        return_url=_settings.payment_return_url,
    )
    await crud.set_provider_ref(db, payment, init.provider_ref)

    if init.settled:  # e.g. mock provider — settle now and fan out
        if await crud.mark_succeeded(db, payment):
            await _publish_succeeded(payment)
            await _maybe_reward_referral(db, payment)
        return CheckoutResponse(payment_id=payment.id, status="succeeded",
                                amount_cents=payment.amount_cents, currency=payment.currency)

    return CheckoutResponse(payment_id=payment.id, status="pending",
                            amount_cents=payment.amount_cents, currency=payment.currency,
                            payment_url=init.payment_url)


@router.post("/webhook/{provider_name}")
async def payment_webhook(
    provider_name: str, request: Request, db: AsyncSession = Depends(get_db)
) -> dict:
    """Gateway callback → mark the payment paid and fan out (idempotent)."""
    provider = get_provider()
    # Accept form-encoded (Paybox) or JSON callbacks.
    try:
        form = await request.form()
        params = dict(form) if form else {}
    except Exception:
        params = {}
    if not params:
        try:
            params = await request.json()
        except Exception:
            params = {}

    try:
        result = provider.parse_webhook(params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payment = None
    if result.order_id:
        try:
            payment = await crud.get(db, uuid.UUID(result.order_id))
        except ValueError:
            payment = None
    if payment is None and result.provider_ref:
        payment = await crud.get_by_provider_ref(db, result.provider_ref)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    if result.succeeded and await crud.mark_succeeded(db, payment):
        await _publish_succeeded(payment)
        await _maybe_reward_referral(db, payment)
    return {"status": "ok"}


@router.get("/me", response_model=list[PaymentOut])
async def my_payments(
    role: str = Query(default="student", pattern="^(student|tutor)$"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentOut]:
    items = await crud.list_for_user(db, uuid.UUID(user.id), role)
    return [PaymentOut.model_validate(p) for p in items]


@router.post("/packages/checkout", response_model=LessonPackageOut, status_code=201)
async def checkout_package(
    payload: PackageCheckoutRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonPackageOut:
    """Buy a discounted bundle of lessons with one tutor, paid in full now.

    The tutor is credited the whole package's earnings immediately (same as
    any other payment) — booking only draws down ``lessons_remaining`` per
    lesson scheduled against it, it never charges again.
    """
    try:
        tutor = await _tutors.get(f"/tutors/{payload.tutor_id}")
    except ServiceError as exc:
        if exc.status == 404:
            raise HTTPException(status_code=404, detail="Tutor not found") from exc
        raise HTTPException(status_code=502, detail="Could not verify tutor") from exc
    per_lesson = tutor.get("price_cents")
    if not per_lesson:
        raise HTTPException(status_code=409, detail="Tutor has no price set")
    currency = tutor.get("currency", "USD")
    total = crud.package_price(int(per_lesson), payload.lesson_count)

    provider = get_provider()
    payment = await crud.create_payment(
        db,
        student_id=uuid.UUID(user.id),
        tutor_id=payload.tutor_id,
        booking_id=None,
        total_cents=total,
        currency=currency,
        rate=_settings.commission_rate,
        gateway=provider.name,
        quantity=payload.lesson_count,
    )
    init = await provider.create(
        amount_cents=total, currency=currency, order_id=str(payment.id),
        description=f"{payload.lesson_count}-lesson package with tutor {payload.tutor_id}",
        return_url=_settings.payment_return_url,
    )
    await crud.set_provider_ref(db, payment, init.provider_ref)
    if not init.settled:
        # Real gateways would redirect first; the package is only created
        # once the payment actually succeeds (via the webhook, mirroring
        # /checkout). The mock provider always settles immediately, so this
        # branch only matters once a real PSP is wired in.
        raise HTTPException(status_code=402, detail="Payment pending — complete it via payment_url")
    await crud.mark_succeeded(db, payment)
    await _publish_succeeded(payment)
    await _maybe_reward_referral(db, payment)
    package = await crud.create_package(
        db, student_id=uuid.UUID(user.id), tutor_id=payload.tutor_id, payment_id=payment.id,
        total_lessons=payload.lesson_count, price_cents=total, currency=currency,
    )
    return LessonPackageOut.model_validate(package)


@router.get("/packages/me", response_model=list[LessonPackageOut])
async def my_packages(
    user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[LessonPackageOut]:
    items = await crud.list_packages_for_student(db, uuid.UUID(user.id))
    return [LessonPackageOut.model_validate(p) for p in items]


@router.post("/packages/{package_id}/consume", response_model=LessonPackageOut)
async def consume_package(
    package_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonPackageOut:
    """Called by Booking (forwarding the student's own token) when a lesson is
    scheduled against a package instead of a fresh payment."""
    package = await crud.get_package(db, package_id)
    if package is None or package.student_id != uuid.UUID(user.id):
        raise HTTPException(status_code=404, detail="Package not found")
    if package.lessons_remaining <= 0:
        raise HTTPException(status_code=409, detail="Package has no lessons remaining")
    return LessonPackageOut.model_validate(await crud.consume_package_lesson(db, package))


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentOut:
    payment = await crud.get(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if uuid.UUID(user.id) not in (payment.student_id, payment.tutor_id):
        raise HTTPException(status_code=403, detail="Not your payment")
    return PaymentOut.model_validate(payment)


@router.get("/{payment_id}/receipt", response_model=Receipt)
async def get_receipt(
    payment_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Receipt:
    payment = await crud.get(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if uuid.UUID(user.id) not in (payment.student_id, payment.tutor_id):
        raise HTTPException(status_code=403, detail="Not your payment")
    return Receipt(
        payment_id=payment.id,
        issued_at=payment.created_at,
        student_id=payment.student_id,
        tutor_id=payment.tutor_id,
        quantity=payment.quantity,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        commission_cents=payment.commission_cents,
        tutor_earnings_cents=payment.tutor_earnings_cents,
        status=payment.status,
    )


@router.post("/{payment_id}/refund", response_model=RefundOut, status_code=201)
async def refund_payment(
    payment_id: uuid.UUID,
    payload: RefundRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RefundOut:
    payment = await crud.get(db, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    # Student who paid, or staff, may request a refund.
    if uuid.UUID(user.id) != payment.student_id and user.role not in (
        "admin", "super_admin", "finance_manager", "support_manager"
    ):
        raise HTTPException(status_code=403, detail="Not allowed to refund this payment")

    already = await crud.refunded_total(payment)
    remaining = payment.amount_cents - already
    if remaining <= 0:
        raise HTTPException(status_code=409, detail="Payment already fully refunded")
    amount = payload.amount_cents or remaining
    if amount > remaining:
        raise HTTPException(status_code=400, detail=f"Refund exceeds remaining {remaining}")

    refund = await crud.add_refund(db, payment, amount, payload.reason)
    await bus.publish(
        Topics.PAYMENT_REFUNDED,
        {
            "payment_id": str(payment.id),
            "student_id": str(payment.student_id),
            "tutor_id": str(payment.tutor_id),
            "amount_cents": amount,
        },
        key=str(payment.tutor_id),
    )
    return RefundOut.model_validate(refund)
