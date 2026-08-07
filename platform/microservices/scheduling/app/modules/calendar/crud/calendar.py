"""Calendar persistence + slot generation."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.calendar import AvailabilityRule, BlockedTime


async def replace_rules(
    db: AsyncSession, tutor_id: uuid.UUID, rules: list[dict]
) -> list[AvailabilityRule]:
    existing = await db.execute(
        select(AvailabilityRule).where(AvailabilityRule.tutor_id == tutor_id)
    )
    for row in existing.scalars().all():
        await db.delete(row)
    created = [AvailabilityRule(tutor_id=tutor_id, **r) for r in rules]
    db.add_all(created)
    await db.commit()
    return await list_rules(db, tutor_id)


async def list_rules(db: AsyncSession, tutor_id: uuid.UUID) -> list[AvailabilityRule]:
    result = await db.execute(
        select(AvailabilityRule)
        .where(AvailabilityRule.tutor_id == tutor_id)
        .order_by(AvailabilityRule.weekday, AvailabilityRule.start_time)
    )
    return list(result.scalars().all())


async def add_blocked(db: AsyncSession, tutor_id: uuid.UUID, data: dict) -> BlockedTime:
    blocked = BlockedTime(tutor_id=tutor_id, **data)
    db.add(blocked)
    await db.commit()
    await db.refresh(blocked)
    return blocked


async def delete_blocked(db: AsyncSession, tutor_id: uuid.UUID, blocked_id: uuid.UUID) -> bool:
    blocked = await db.get(BlockedTime, blocked_id)
    if blocked is None or blocked.tutor_id != tutor_id:
        return False
    await db.delete(blocked)
    await db.commit()
    return True


async def list_blocked(
    db: AsyncSession, tutor_id: uuid.UUID, start: datetime, end: datetime
) -> list[BlockedTime]:
    result = await db.execute(
        select(BlockedTime).where(
            BlockedTime.tutor_id == tutor_id,
            BlockedTime.start < end,
            BlockedTime.end > start,
        )
    )
    return list(result.scalars().all())


async def is_available(
    db: AsyncSession, tutor_id: uuid.UUID, start: datetime, end: datetime
) -> bool:
    """Whether [start, end) fits inside the tutor's calendar.

    Used by Booking before it accepts a reservation — see
    ``modules/booking/api/routes/bookings.py``. Two rules, in order:

    1. If the tutor has never configured availability rules, calendar
       enforcement is skipped (only the existing overlap-with-other-bookings
       check applies) — otherwise every tutor who hasn't gotten around to
       setting up their calendar yet would be unbookable, which is worse than
       not validating at all.
    2. Once rules exist, the requested window must fit entirely inside one
       rule for that weekday, and must not intersect a blocked time. This is
       the check that used to be entirely missing: a tutor with a 9-to-5
       calendar could previously be booked for 3 a.m.
    """
    rules = await list_rules(db, tutor_id)
    if not rules:
        return True
    # Rule times are wall-clock UTC (see generate_slots, which combines them
    # with tzinfo=timezone.utc) — normalise the requested window the same way
    # before comparing, regardless of what offset the caller sent.
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    if start_utc.date() != (end_utc - timedelta(microseconds=1)).date():
        # A booking that crosses midnight can never fit a single day's rule.
        return False
    weekday = start_utc.weekday()
    fits_a_rule = any(
        r.weekday == weekday
        and start_utc.time() >= r.start_time
        and end_utc.time() <= r.end_time
        for r in rules
    )
    if not fits_a_rule:
        return False
    blocked = await list_blocked(db, tutor_id, start, end)
    return len(blocked) == 0


async def generate_slots(
    db: AsyncSession,
    tutor_id: uuid.UUID,
    date_from: date,
    date_to: date,
    slot_minutes: int,
) -> list[dict]:
    """Concrete bookable slots between two dates from rules minus blocked times."""
    rules = await list_rules(db, tutor_id)
    rules_by_day: dict[int, list[AvailabilityRule]] = {}
    for r in rules:
        rules_by_day.setdefault(r.weekday, []).append(r)

    range_start = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
    range_end = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
    blocked = await list_blocked(db, tutor_id, range_start, range_end)

    def is_blocked(s: datetime, e: datetime) -> bool:
        return any(b.start < e and b.end > s for b in blocked)

    slots: list[dict] = []
    delta = timedelta(minutes=slot_minutes)
    current = date_from
    while current <= date_to:
        for rule in rules_by_day.get(current.weekday(), []):
            cursor = datetime.combine(current, rule.start_time, tzinfo=timezone.utc)
            day_end = datetime.combine(current, rule.end_time, tzinfo=timezone.utc)
            while cursor + delta <= day_end:
                slot_end = cursor + delta
                if not is_blocked(cursor, slot_end):
                    slots.append({"start": cursor, "end": slot_end})
                cursor = slot_end
        current += timedelta(days=1)
    return slots
