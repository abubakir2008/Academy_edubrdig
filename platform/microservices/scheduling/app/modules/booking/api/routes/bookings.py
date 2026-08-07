"""Booking endpoints (namespaced under /booking)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.clients import ServiceClient, ServiceError, service_url
from edubridge_shared.events import Topics
from edubridge_shared.fastapi_auth import CurrentUser

from ....calendar.crud import calendar as calendar_crud
from ...crud import booking as crud
from ...db.session import get_db
from ...events import bus

_tutors = ServiceClient(service_url("tutors"))
_finance = ServiceClient(service_url("payments"))
from ...models.booking import BookingStatus
from ...schemas.booking import (
    BookingCancel,
    BookingCreate,
    BookingOut,
    BookingReschedule,
)
from ..deps import get_current_user

router = APIRouter(prefix="/booking", tags=["booking"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingOut:
    # Authoritative price + existence check from the Tutor service (GET is public).
    try:
        tutor = await _tutors.get(f"/tutors/{payload.tutor_id}")
    except ServiceError as exc:
        if exc.status == 404:
            raise HTTPException(status_code=404, detail="Tutor not found") from exc
        raise HTTPException(status_code=502, detail="Could not verify tutor") from exc
    if not tutor.get("is_verified", False):
        # Allow booking unverified tutors? Business choice — here we only require active.
        pass
    price = tutor.get("trial_price_cents") if payload.is_trial else tutor.get("price_cents")
    if price is None:
        raise HTTPException(status_code=409, detail="Tutor has no price set for this lesson type")
    currency = tutor.get("currency", "USD")

    end = payload.scheduled_start + timedelta(minutes=payload.duration_minutes)
    if await crud.has_overlap(db, payload.tutor_id, payload.scheduled_start, end):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The tutor already has a booking in this time slot",
        )
    # Calendar used to be consulted nowhere at all — a tutor with a 9-to-5
    # schedule could be booked at 3 a.m. Booking and Calendar now share one
    # department/session, so this is an in-process check, not a network call.
    if not await calendar_crud.is_available(db, payload.tutor_id, payload.scheduled_start, end):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The tutor is not available at the requested time",
        )
    if payload.is_trial and await crud.has_used_trial(db, uuid.UUID(user.id), payload.tutor_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You've already used your trial lesson with this tutor",
        )
    if payload.package_id is not None:
        # Finance owns the package's balance; Booking only asks it to draw one
        # down, forwarding the student's own token (same pattern as the tutor
        # price lookup above) rather than trusting the client's word for it.
        token = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        try:
            await _finance.post(f"/payments/packages/{payload.package_id}/consume", token=token)
        except ServiceError as exc:
            raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
    data = payload.model_dump()
    data["price_cents"] = int(price)
    data["currency"] = currency
    booking = await crud.create(db, uuid.UUID(user.id), data)
    await bus.publish(
        Topics.BOOKING_CREATED,
        {
            "booking_id": str(booking.id),
            "student_id": str(booking.student_id),
            "tutor_id": str(booking.tutor_id),
            "scheduled_start": booking.scheduled_start.isoformat(),
            "duration_minutes": booking.duration_minutes,
            "is_trial": booking.is_trial,
        },
        key=str(booking.tutor_id),
    )
    return BookingOut.model_validate(booking)


@router.get("/me", response_model=list[BookingOut])
async def my_bookings(
    role: str = Query(default="student", pattern="^(student|tutor)$"),
    status_filter: str | None = Query(default=None, alias="status"),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BookingOut]:
    items = await crud.list_for_user(db, uuid.UUID(user.id), role, status_filter)
    return [BookingOut.model_validate(b) for b in items]


async def _get_owned(db: AsyncSession, booking_id: uuid.UUID, user_id: uuid.UUID):
    booking = await crud.get(db, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if user_id not in (booking.student_id, booking.tutor_id):
        raise HTTPException(status_code=403, detail="Not your booking")
    return booking


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingOut:
    booking = await _get_owned(db, booking_id, uuid.UUID(user.id))
    return BookingOut.model_validate(booking)


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


@router.get("/{booking_id}/ics")
async def booking_ics(
    booking_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """A downloadable .ics so a student/tutor can drop the lesson into their own
    calendar app — no OAuth dance with Google/Outlook, just a static file."""
    booking = await _get_owned(db, booking_id, uuid.UUID(user.id))
    fmt = "%Y%m%dT%H%M%SZ"
    summary = "Пробный урок" if booking.is_trial else "Урок"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EduBridge//Booking//RU",
        "BEGIN:VEVENT",
        f"UID:{booking.id}@edubridge",
        f"DTSTAMP:{datetime.now(tz=timezone.utc).strftime(fmt)}",
        f"DTSTART:{booking.scheduled_start.astimezone(timezone.utc).strftime(fmt)}",
        f"DTEND:{booking.scheduled_end.astimezone(timezone.utc).strftime(fmt)}",
        f"SUMMARY:{_ics_escape(summary)} — EduBridge",
        f"DESCRIPTION:{_ics_escape(f'{summary}, {booking.duration_minutes} мин.')}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    ics = "\r\n".join(lines) + "\r\n"
    return Response(
        content=ics,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="lesson-{booking.id}.ics"'},
    )


@router.post("/{booking_id}/confirm", response_model=BookingOut)
async def confirm_booking(
    booking_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingOut:
    booking = await _get_owned(db, booking_id, uuid.UUID(user.id))
    if booking.tutor_id != uuid.UUID(user.id):
        raise HTTPException(status_code=403, detail="Only the tutor can confirm")
    if booking.status != BookingStatus.PENDING.value:
        raise HTTPException(status_code=409, detail=f"Cannot confirm a {booking.status} booking")
    booking.status = BookingStatus.CONFIRMED.value
    saved = await crud.save(db, booking)
    # Lessons service will auto-create the lesson; notifications informs the student.
    await bus.publish(
        Topics.BOOKING_CONFIRMED,
        {
            "booking_id": str(saved.id),
            "student_id": str(saved.student_id),
            "tutor_id": str(saved.tutor_id),
            "scheduled_start": saved.scheduled_start.isoformat(),
            "duration_minutes": saved.duration_minutes,
            "is_trial": saved.is_trial,
        },
        key=str(saved.id),
    )
    return BookingOut.model_validate(saved)


@router.post("/{booking_id}/reschedule", response_model=BookingOut)
async def reschedule_booking(
    booking_id: uuid.UUID,
    payload: BookingReschedule,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingOut:
    booking = await _get_owned(db, booking_id, uuid.UUID(user.id))
    if booking.status not in (BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value):
        raise HTTPException(status_code=409, detail=f"Cannot reschedule a {booking.status} booking")
    duration = payload.duration_minutes or booking.duration_minutes
    new_end = payload.scheduled_start + timedelta(minutes=duration)
    if await crud.has_overlap(db, booking.tutor_id, payload.scheduled_start, new_end, exclude_id=booking.id):
        raise HTTPException(status_code=409, detail="The tutor is busy at the new time")
    if not await calendar_crud.is_available(db, booking.tutor_id, payload.scheduled_start, new_end):
        raise HTTPException(status_code=409, detail="The tutor is not available at the new time")
    booking.scheduled_start = payload.scheduled_start
    booking.scheduled_end = new_end
    booking.duration_minutes = duration
    return BookingOut.model_validate(await crud.save(db, booking))


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID,
    payload: BookingCancel,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingOut:
    booking = await _get_owned(db, booking_id, uuid.UUID(user.id))
    if booking.status in (BookingStatus.CANCELLED.value, BookingStatus.COMPLETED.value):
        raise HTTPException(status_code=409, detail=f"Booking already {booking.status}")
    booking.status = BookingStatus.CANCELLED.value
    booking.cancel_reason = payload.reason
    saved = await crud.save(db, booking)
    await bus.publish(
        Topics.BOOKING_CANCELLED,
        {
            "booking_id": str(saved.id),
            "student_id": str(saved.student_id),
            "tutor_id": str(saved.tutor_id),
            "cancelled_by": user.id,
        },
        key=str(saved.id),
    )
    return BookingOut.model_validate(saved)


@router.post("/{booking_id}/complete", response_model=BookingOut)
async def complete_booking(
    booking_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BookingOut:
    booking = await _get_owned(db, booking_id, uuid.UUID(user.id))
    if booking.tutor_id != uuid.UUID(user.id):
        raise HTTPException(status_code=403, detail="Only the tutor can complete")
    if booking.status != BookingStatus.CONFIRMED.value:
        raise HTTPException(status_code=409, detail="Only confirmed bookings can be completed")
    booking.status = BookingStatus.COMPLETED.value
    return BookingOut.model_validate(await crud.save(db, booking))
