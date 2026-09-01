"""Periodic "your lesson is starting soon" push reminder.

Unlike `edubridge_shared.events` (which reacts to something that already
happened), a reminder fires because a lesson is *approaching* its start time
on the clock — nothing changes to trigger it, so the event bus doesn't fit.
The platform has no separate scheduler/cron process (see platform/README.md's
Roadmap), so this runs as its own background asyncio task inside the calendar
app, started/stopped the same way `edubridge_shared.events.EventBus` runs its
consumer loop (`create_task` on start, cancel-and-await on stop).

Notifies the lesson's teacher only, via engagement's internal endpoint
(`POST /notifications/internal`, guarded by the shared internal secret — the
poller has no end-user JWT to present). Reminding enrolled students too would
need a way to read a course's roster without a user token, which academics
doesn't expose yet — a natural follow-up, not done here.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from edubridge_shared.cache import Cache
from edubridge_shared.clients import ServiceClient, service_url

from ..core.config import get_settings
from ..db.session import SessionLocal
from ..models.lesson import Lesson, LessonStatus

log = logging.getLogger("calendar.reminder")

POLL_INTERVAL_SECONDS = 60
REMINDER_LEAD_MINUTES = 10
#: How long a lesson's dedupe marker survives — comfortably longer than the
#: reminder window, so a lesson already reminded this run never fires twice.
DEDUPE_TTL_SECONDS = 3600

_settings = get_settings()
_cache = Cache(_settings.cache_redis_url)
_notifications = ServiceClient(service_url("notifications"))


class ReminderScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stopping = False

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _loop(self) -> None:
        while not self._stopping:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("Reminder tick failed: %s", exc)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _tick(self) -> None:
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=REMINDER_LEAD_MINUTES)
        async with SessionLocal() as db:
            result = await db.execute(
                select(Lesson).where(
                    Lesson.status == LessonStatus.SCHEDULED.value,
                    Lesson.scheduled_start >= now,
                    Lesson.scheduled_start <= window_end,
                )
            )
            lessons = list(result.scalars().all())

        for lesson in lessons:
            dedupe_key = f"lesson_reminder:{lesson.id}"
            if await _cache.get(dedupe_key) is not None:
                continue
            # Mark first, so a slow/failed notify doesn't leave the window
            # open for the next tick (60s later) to double-send.
            await _cache.set(dedupe_key, True, ttl_seconds=DEDUPE_TTL_SECONDS)
            await self._notify(lesson)

    async def _notify(self, lesson: Lesson) -> None:
        when = lesson.scheduled_start.strftime("%H:%M")
        try:
            await _notifications.post(
                "/internal",
                json={
                    "user_id": str(lesson.teacher_id),
                    "type": "lesson_reminder",
                    "title": "Урок скоро начнётся",
                    "body": f"{lesson.title or 'Урок'} в {when}",
                    "channel": "push",
                },
            )
        except Exception as exc:
            log.warning("Failed to send reminder for lesson %s: %s", lesson.id, exc)


scheduler = ReminderScheduler()
