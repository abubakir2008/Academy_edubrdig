"""Minimal iCalendar (RFC 5545) rendering — no external dependency needed for
a handful of VEVENT blocks with no recurrence rules of their own (each
recurring lesson is already a materialized row, not an RRULE)."""

from __future__ import annotations

from datetime import datetime, timezone

from ..models.lesson import Lesson, LessonStatus

_ICS_STATUS = {
    LessonStatus.SCHEDULED.value: "CONFIRMED",
    LessonStatus.COMPLETED.value: "CONFIRMED",
    LessonStatus.CANCELLED.value: "CANCELLED",
}


def _stamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def render_ics(lessons: list[Lesson]) -> str:
    now = _stamp(datetime.now(tz=timezone.utc))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//EduBridge//Calendar//RU", "CALSCALE:GREGORIAN"]
    for lesson in lessons:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{lesson.id}@edubridge",
            f"DTSTAMP:{now}",
            f"DTSTART:{_stamp(lesson.scheduled_start)}",
            f"DTEND:{_stamp(lesson.scheduled_end)}",
            "SUMMARY:Lesson",
            f"STATUS:{_ICS_STATUS.get(lesson.status, 'CONFIRMED')}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
