"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Video } from "lucide-react";

import { get, put } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Course, Lesson } from "@/lib/types";

function formatWhen(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const dateLabel = start.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
  const startLabel = start.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  const endLabel = end.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  return `${dateLabel}, ${startLabel}–${endLabel}`;
}

/**
 * "Next lesson" card for the dashboard overview — shown right after the
 * weekly calendar, for both students and tutors. Zoom join is only ever
 * clickable while the lesson is actually running (scheduled_start ≤ now ≤
 * scheduled_end); the card itself turns green for exactly that window and
 * stays grey the rest of the time. A lesson whose end time passed while it
 * was still "scheduled" comes back from the API already as "missed" (see
 * calendar department's _lesson_out) — a tutor can still mark it completed
 * from here if it did happen.
 */
export function NextLessonCard({ courses }: { courses: Course[] | null }) {
  const { user } = useAuth();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    get<Lesson[]>("/calendar/lessons/me", true)
      .catch(() => [] as Lesson[])
      .then((l) => {
        setLessons(l);
        setLoaded(true);
      });
  }, []);

  // Ticks the join window open/closed and the green/grey state live, without
  // needing a page refresh right as a lesson starts or ends.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  const courseById = useMemo(() => new Map((courses ?? []).map((c) => [c.id, c])), [courses]);

  const lesson = useMemo(() => {
    const upcoming = lessons
      .filter((l) => l.status !== "cancelled" && new Date(l.scheduled_end).getTime() >= now)
      .sort((a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime());
    return upcoming[0] ?? null;
  }, [lessons, now]);

  async function markCompleted() {
    if (!lesson) return;
    setBusy(true);
    await put(`/calendar/lessons/${lesson.id}`, { status: "completed" }, true).catch(() => undefined);
    const fresh = await get<Lesson[]>("/calendar/lessons/me", true).catch(() => lessons);
    setLessons(fresh);
    setBusy(false);
  }

  if (!user || (user.role !== "student" && user.role !== "tutor")) return null;
  if (!loaded) return null;
  if (!lesson) {
    return (
      <section className="card mt-8 p-6">
        <h2 className="display text-lg">Ближайший урок</h2>
        <p className="mt-2 text-sm text-ink-3">Ближайших уроков нет.</p>
      </section>
    );
  }

  const start = new Date(lesson.scheduled_start).getTime();
  const end = new Date(lesson.scheduled_end).getTime();
  const isActive = lesson.status === "scheduled" && now >= start && now <= end;
  const isUpcoming = lesson.status === "scheduled" && now < start;
  const isMissed = lesson.status === "missed";
  const isCompleted = lesson.status === "completed";
  const isCancelled = lesson.status === "cancelled";
  const canFinalize = lesson.status === "scheduled" || lesson.status === "missed";

  const course = courseById.get(lesson.course_id);
  const courseTitle = course?.title ?? "Курс";

  const statusText = isActive
    ? "Урок идёт сейчас"
    : isUpcoming
      ? `Начнётся: ${formatWhen(lesson.scheduled_start, lesson.scheduled_end)}`
      : isMissed
        ? "Урок не состоялся"
        : isCompleted
          ? "Урок завершён"
          : isCancelled
            ? "Урок отменён"
            : formatWhen(lesson.scheduled_start, lesson.scheduled_end);

  return (
    <section
      className={`card mt-8 p-6 transition-colors ${
        isActive ? "border-jade-400 bg-jade-50" : "border-line bg-paper"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <span
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${
              isActive ? "bg-jade-500 text-white" : "bg-paper-2 text-ink-3"
            }`}
            aria-hidden
          >
            <Video className="h-5 w-5" strokeWidth={2} />
          </span>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-aurora-600">
              Ближайший урок
            </p>
            <h2 className="display mt-1 text-lg">{lesson.title || courseTitle}</h2>
            <p className="mt-0.5 text-xs text-ink-3">{courseTitle}</p>
            {(lesson.description || course?.description) && (
              <p className="mt-1 max-w-md text-sm text-ink-3">{lesson.description || course?.description}</p>
            )}
            <p className={`mt-2 text-sm font-medium ${isActive ? "text-jade-700" : "text-ink-2"}`}>
              {statusText}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-stretch gap-2 sm:items-end">
          {lesson.meeting_url && (
            <a
              href={isActive ? lesson.meeting_url : undefined}
              target="_blank"
              rel="noreferrer"
              aria-disabled={!isActive}
              className={`btn !py-2 text-sm ${
                isActive ? "btn-primary" : "btn-ghost pointer-events-none opacity-50"
              }`}
              title={isActive ? undefined : "Вход откроется только во время урока"}
            >
              Войти на урок
            </a>
          )}
          {user.role === "tutor" && isActive && lesson.start_url && (
            <a href={lesson.start_url} target="_blank" rel="noreferrer" className="btn btn-ghost !py-2 text-sm">
              Начать как хост
            </a>
          )}
          {user.role === "tutor" && (
            <div className="flex gap-2">
              {canFinalize && (
                <button className="btn btn-ghost !py-2 text-xs" disabled={busy} onClick={() => void markCompleted()}>
                  Отметить проведённым
                </button>
              )}
              <Link
                href={`/dashboard/courses/${lesson.course_id}/calendar`}
                className="btn btn-ghost !py-2 text-xs"
              >
                Редактировать
              </Link>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
