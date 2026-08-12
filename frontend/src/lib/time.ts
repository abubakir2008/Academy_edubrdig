/**
 * Lesson times are always Kyrgyzstan wall-clock time — the platform, its
 * tutors and its students are all there. Bishkek is a fixed UTC+6 with no
 * DST (no seasonal shift since 2005), so a hardcoded offset is enough; no
 * timezone library needed.
 *
 * Without this, a `<input type="date">`/`<input type="time">` pair parsed
 * via a bare `new Date(...)` is interpreted in the *browser's* timezone —
 * a tutor whose laptop clock is set to another timezone would silently
 * schedule lessons at the wrong wall-clock hour for everyone else. Same
 * problem in reverse for display: `toLocaleTimeString` without an explicit
 * `timeZone` shows each viewer their own local hour instead of the lesson's
 * actual Bishkek time.
 */

export const APP_TIMEZONE = "Asia/Bishkek";
const APP_UTC_OFFSET = "+06:00";

/** Combines a `YYYY-MM-DD` + `HH:MM` pair (both meant as Bishkek time) into
 * a correct UTC ISO string, regardless of the browser's own timezone. */
export function bishkekInputToISO(date: string, time: string): string {
  return new Date(`${date}T${time}:00${APP_UTC_OFFSET}`).toISOString();
}

export function formatBishkekTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", {
    timeZone: APP_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatBishkekDate(iso: string, opts: Intl.DateTimeFormatOptions = {}): string {
  return new Date(iso).toLocaleDateString("ru-RU", { timeZone: APP_TIMEZONE, ...opts });
}

export function formatBishkekDateTime(iso: string, opts: Intl.DateTimeFormatOptions = {}): string {
  return new Date(iso).toLocaleString("ru-RU", { timeZone: APP_TIMEZONE, ...opts });
}

/**
 * Single source of truth for "can this lesson be joined right now" — used
 * everywhere a Zoom join link appears (dashboard's next-lesson card, the
 * weekly calendar's selected-lesson panel, the course lesson list), so the
 * rule can never drift between them: only while the lesson is actually
 * running, never before, and never after (a `scheduled` lesson whose end
 * time already passed reads back from the API as `missed`, which this
 * already excludes since it isn't `scheduled`).
 */
export function isLessonJoinable(lesson: { status: string; scheduled_start: string; scheduled_end: string }): boolean {
  const now = Date.now();
  const start = new Date(lesson.scheduled_start).getTime();
  const end = new Date(lesson.scheduled_end).getTime();
  return lesson.status === "scheduled" && now >= start && now <= end;
}
