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
 * everywhere a "join the call" link appears (dashboard's next-lesson card, the
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

export type LessonVisualStatus = "missed" | "completed" | "active" | "upcoming" | "cancelled";

/**
 * One shared classification for how a lesson should be color-coded
 * everywhere its status is shown — missed (red), completed (green), active
 * right now / joinable (blue), upcoming / not started yet (no accent),
 * cancelled (muted). Built on `isLessonJoinable` so the two can never
 * disagree about what "active" means.
 */
export function lessonVisualStatus(lesson: {
  status: string;
  scheduled_start: string;
  scheduled_end: string;
}): LessonVisualStatus {
  if (lesson.status === "cancelled") return "cancelled";
  if (lesson.status === "missed") return "missed";
  if (lesson.status === "completed") return "completed";
  return isLessonJoinable(lesson) ? "active" : "upcoming";
}

/** Shared card border/background per status — every full-card lesson
 * treatment (the course's lesson list, the dashboard's next-lesson card)
 * uses exactly these classes so the four colors mean the same thing
 * everywhere. Only shades that actually exist in `globals.css`'s `@theme`
 * are used here (jade/coral only have -100/-500/-700 defined). */
export const LESSON_STATUS_CARD_CLASS: Record<LessonVisualStatus, string> = {
  missed: "border-coral-500 bg-coral-100",
  completed: "border-jade-500 bg-jade-100",
  active: "border-aurora-500 bg-aurora-50",
  upcoming: "border-line bg-paper",
  cancelled: "border-line bg-paper-2 opacity-60",
};
