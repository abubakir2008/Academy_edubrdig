"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { CalendarClock, CalendarRange, ChevronLeft, ChevronRight } from "lucide-react";

import { get } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Course, Lesson, LessonStatus } from "@/lib/types";

const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_PX = 56;
const WEEKDAY_LABELS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

/** Course accent — cycles through the design system's four brand hues so
 * lessons from different courses stay visually distinct on the grid. */
const COURSE_STYLES = [
  { bg: "bg-aurora-50", border: "border-aurora-500", dot: "bg-aurora-600" },
  { bg: "bg-citrus-100", border: "border-citrus-500", dot: "bg-citrus-500" },
  { bg: "bg-jade-100", border: "border-jade-500", dot: "bg-jade-500" },
  { bg: "bg-coral-100", border: "border-coral-500", dot: "bg-coral-500" },
];

const STATUS_LABEL: Record<LessonStatus, string> = {
  scheduled: "Запланирован",
  completed: "Проведён",
  cancelled: "Отменён",
  missed: "Не состоялся",
};

function startOfDay(d: Date): Date {
  const date = new Date(d);
  date.setHours(0, 0, 0, 0);
  return date;
}

function startOfWeek(d: Date): Date {
  const date = startOfDay(d);
  const day = date.getDay(); // 0 = Sunday
  const diffToMonday = day === 0 ? -6 : 1 - day;
  date.setDate(date.getDate() + diffToMonday);
  return date;
}

function isToday(d: Date): boolean {
  return d.toDateString() === new Date().toDateString();
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function formatWeekRange(start: Date, end: Date): string {
  const startLabel = start.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
  const endLabel = end.toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric" });
  return `${startLabel} – ${endLabel}`;
}

/**
 * Advanced weekly lessons calendar for the dashboard Overview page. Reads
 * `/calendar/lessons/me` — already returns the right set for either role
 * (a tutor's own lessons, or a student's lessons across every course they're
 * enrolled in). `courses` (for labelling/coloring blocks) comes from the
 * parent, which fetches `/courses/me` once and shares it with `MyStudents`
 * too, instead of each component fetching its own copy. Purely read-only:
 * full lesson management (create/edit/delete/recurrence) stays on the
 * per-course calendar page this links out to.
 */
export function LessonsCalendar({ courses }: { courses: Course[] | null }) {
  const { user } = useAuth();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [weekOffset, setWeekOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    get<Lesson[]>("/calendar/lessons/me", true)
      .catch(() => [] as Lesson[])
      .then((l) => {
        setLessons(l);
        setLoaded(true);
      });
  }, []);

  const courseTitleById = useMemo(
    () => new Map((courses ?? []).map((c) => [c.id, c.title])),
    [courses],
  );
  const courseTitle = (courseId: string) => courseTitleById.get(courseId) ?? "Курс";

  const courseIds = useMemo(
    () => Array.from(new Set(lessons.map((l) => l.course_id))).sort(),
    [lessons],
  );
  const courseColor = (courseId: string) => {
    const idx = courseIds.indexOf(courseId);
    return COURSE_STYLES[(idx < 0 ? 0 : idx) % COURSE_STYLES.length];
  };

  const weekStart = useMemo(() => {
    const start = startOfWeek(new Date());
    start.setDate(start.getDate() + weekOffset * 7);
    return start;
  }, [weekOffset]);
  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, i) => new Date(weekStart.getTime() + i * DAY_MS)),
    [weekStart],
  );

  const lessonsByDay = useMemo(() => {
    const buckets: Lesson[][] = Array.from({ length: 7 }, () => []);
    for (const lesson of lessons) {
      const dayIdx = Math.round(
        (startOfDay(new Date(lesson.scheduled_start)).getTime() - weekStart.getTime()) / DAY_MS,
      );
      if (dayIdx >= 0 && dayIdx < 7) buckets[dayIdx].push(lesson);
    }
    return buckets;
  }, [lessons, weekStart]);

  const { hourStart, hourEnd } = useMemo(() => {
    const inWeek = lessonsByDay.flat();
    if (inWeek.length === 0) return { hourStart: 9, hourEnd: 18 };
    let min = 24;
    let max = 0;
    for (const l of inWeek) {
      const start = new Date(l.scheduled_start);
      const end = new Date(l.scheduled_end);
      min = Math.min(min, start.getHours());
      max = Math.max(max, end.getHours() + (end.getMinutes() > 0 ? 1 : 0));
    }
    return { hourStart: Math.max(0, min - 1), hourEnd: Math.min(24, Math.max(max + 1, min + 2)) };
  }, [lessonsByDay]);

  const hourMarks = useMemo(
    () => Array.from({ length: hourEnd - hourStart }, (_, i) => hourStart + i),
    [hourStart, hourEnd],
  );
  const gridHeight = (hourEnd - hourStart) * HOUR_PX;

  function blockStyle(lesson: Lesson): CSSProperties {
    const start = new Date(lesson.scheduled_start);
    const end = new Date(lesson.scheduled_end);
    const rangeStartMin = hourStart * 60;
    const rangeTotalMin = (hourEnd - hourStart) * 60;
    const startMin = start.getHours() * 60 + start.getMinutes();
    const endMin = end.getHours() * 60 + end.getMinutes();
    const top = ((startMin - rangeStartMin) / rangeTotalMin) * 100;
    const height = Math.max(((endMin - startMin) / rangeTotalMin) * 100, 4);
    return { top: `${top}%`, height: `${height}%` };
  }

  const now = Date.now();
  const next7 = lessons.filter((l) => {
    const t = new Date(l.scheduled_start).getTime();
    return l.status !== "cancelled" && t >= now && t < now + 7 * DAY_MS;
  }).length;
  const next30 = lessons.filter((l) => {
    const t = new Date(l.scheduled_start).getTime();
    return l.status !== "cancelled" && t >= now && t < now + 30 * DAY_MS;
  }).length;

  const selected = lessons.find((l) => l.id === selectedId) ?? null;

  if (!user) return null;

  return (
    <section className="card mt-8 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="display text-lg">Расписание занятий</h2>
          <p className="mt-1 text-sm text-ink-3">{formatWeekRange(weekDays[0], weekDays[6])}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip">
            <CalendarClock className="h-3.5 w-3.5" aria-hidden /> За 7 дней: {next7}
          </span>
          <span className="chip">
            <CalendarRange className="h-3.5 w-3.5" aria-hidden /> За 30 дней: {next30}
          </span>
          <div className="flex items-center gap-1">
            <button
              className="btn btn-ghost !p-2"
              onClick={() => setWeekOffset((w) => w - 1)}
              aria-label="Предыдущая неделя"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden />
            </button>
            <button className="btn btn-ghost !px-3 !py-2 text-xs" onClick={() => setWeekOffset(0)}>
              Сегодня
            </button>
            <button
              className="btn btn-ghost !p-2"
              onClick={() => setWeekOffset((w) => w + 1)}
              aria-label="Следующая неделя"
            >
              <ChevronRight className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </div>
      </div>

      {courseIds.length > 1 && (
        <div className="mt-4 flex flex-wrap gap-3">
          {courseIds.map((cid) => (
            <span key={cid} className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-2">
              <span className={`h-2 w-2 rounded-full ${courseColor(cid).dot}`} aria-hidden />
              {courseTitle(cid)}
            </span>
          ))}
        </div>
      )}

      {!loaded ? null : lessons.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-line bg-paper-2 p-6 text-center text-sm text-ink-3">
          {user.role === "tutor"
            ? "Уроков пока нет — запланируйте занятие в разделе курса."
            : "Уроков пока нет — они появятся здесь, как только преподаватель их назначит."}
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto">
          <div className="grid min-w-[720px] grid-cols-[48px_repeat(7,1fr)]">
            <div />
            {weekDays.map((d, i) => (
              <div
                key={i}
                className={`px-2 pb-2 text-center text-xs font-semibold ${
                  isToday(d) ? "text-aurora-700" : "text-ink-2"
                }`}
              >
                {WEEKDAY_LABELS[i]} <span className="text-ink-3">{d.getDate()}</span>
              </div>
            ))}

            <div className="relative" style={{ height: gridHeight }}>
              {hourMarks.map((h) => (
                <div
                  key={h}
                  className="absolute right-2 text-[11px] text-ink-3"
                  style={{ top: `${((h - hourStart) / (hourEnd - hourStart)) * 100}%` }}
                >
                  {String(h).padStart(2, "0")}:00
                </div>
              ))}
            </div>

            {weekDays.map((day, dayIdx) => (
              <div
                key={dayIdx}
                className={`relative border-b border-l border-line ${isToday(day) ? "bg-aurora-50/40" : ""}`}
                style={{ height: gridHeight }}
              >
                {hourMarks.map((h) => (
                  <div
                    key={h}
                    className="absolute inset-x-0 border-t border-line/70"
                    style={{ top: `${((h - hourStart) / (hourEnd - hourStart)) * 100}%` }}
                  />
                ))}
                {lessonsByDay[dayIdx].map((lesson) => {
                  const color = courseColor(lesson.course_id);
                  const cancelled = lesson.status === "cancelled";
                  const missed = lesson.status === "missed";
                  return (
                    <button
                      key={lesson.id}
                      onClick={() => setSelectedId(lesson.id)}
                      className={`absolute inset-x-1 overflow-hidden rounded-lg border-l-[3px] px-2 py-1 text-left text-[11px] leading-tight shadow-sm transition-transform hover:z-10 hover:-translate-y-0.5 ${
                        color.bg
                      } ${color.border} ${cancelled ? "opacity-45 line-through" : ""} ${
                        missed ? "opacity-45" : ""
                      } ${selectedId === lesson.id ? "ring-2 ring-aurora-500" : ""}`}
                      style={blockStyle(lesson)}
                    >
                      <p className="truncate font-semibold text-ink">
                        {lesson.title || courseTitle(lesson.course_id)}
                      </p>
                      <p className="truncate text-ink-3">
                        {formatTime(lesson.scheduled_start)}–{formatTime(lesson.scheduled_end)}
                      </p>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {selected && (
        <div className="mt-6 card border-aurora-300 bg-aurora-50/40 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold">{selected.title || courseTitle(selected.course_id)}</p>
              <p className="text-xs text-ink-3">{courseTitle(selected.course_id)}</p>
              {selected.description && <p className="mt-1 text-sm text-ink-2">{selected.description}</p>}
              <p className="mt-1 text-sm text-ink-2">
                {new Date(selected.scheduled_start).toLocaleString("ru-RU", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
                {" – "}
                {new Date(selected.scheduled_end).toLocaleTimeString("ru-RU", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
              <p className="mt-1 text-xs text-ink-3">{STATUS_LABEL[selected.status]}</p>
            </div>
            <button
              className="text-xs font-semibold text-ink-3 hover:text-ink"
              onClick={() => setSelectedId(null)}
            >
              Закрыть
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-xs font-semibold">
            {selected.meeting_url && (
              <a href={selected.meeting_url} target="_blank" rel="noreferrer" className="text-aurora-700">
                Войти в Zoom →
              </a>
            )}
            {selected.start_url && (
              <a href={selected.start_url} target="_blank" rel="noreferrer" className="text-jade-700">
                Начать как хост →
              </a>
            )}
            <Link href={`/dashboard/courses/${selected.course_id}/calendar`} className="text-ink-2 hover:text-ink">
              Открыть курс →
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
