"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { API_BASE, del, get, post, put, tokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Lesson } from "@/lib/types";

const EMPTY = {
  scheduled_date: "",
  scheduled_time: "",
  duration_minutes: 60,
  recurrence: "none" as "none" | "weekly",
  recurrence_weeks: 4,
};

export default function CourseCalendarPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canManage = user?.role === "tutor" || user?.role === "admin" || user?.role === "super_admin";

  const load = useCallback(async () => {
    if (!user) return;
    if (user.role === "admin" || user.role === "super_admin") {
      const items = await get<Lesson[]>(`/calendar/lessons?course_id=${id}`, true).catch(() => [] as Lesson[]);
      setLessons(items);
      return;
    }
    const items = await get<Lesson[]>("/calendar/lessons/me", true).catch(() => [] as Lesson[]);
    setLessons(items.filter((l) => l.course_id === id));
  }, [id, user]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createLesson() {
    if (!form.scheduled_date || !form.scheduled_time) return;
    setCreating(true);
    setError(null);
    try {
      const scheduled_start = new Date(`${form.scheduled_date}T${form.scheduled_time}:00`).toISOString();
      await post(
        "/calendar/lessons",
        {
          course_id: id,
          scheduled_start,
          duration_minutes: form.duration_minutes,
          recurrence: form.recurrence,
          recurrence_weeks: form.recurrence === "weekly" ? form.recurrence_weeks : undefined,
        },
        true,
      );
      setForm(EMPTY);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать урок — возможно, пересечение по времени");
    } finally {
      setCreating(false);
    }
  }

  async function setStatus(lessonId: string, status: Lesson["status"]) {
    await put(`/calendar/lessons/${lessonId}`, { status }, true).catch(() => undefined);
    await load();
  }

  async function removeLesson(lessonId: string) {
    await del(`/calendar/lessons/${lessonId}`).catch(() => undefined);
    await load();
  }

  async function removeSeries(seriesId: string) {
    await del(`/calendar/series/${seriesId}`).catch(() => undefined);
    await load();
  }

  if (!user) return null;

  // External calendar apps can't send an Authorization header, so the .ics
  // feed is authorized by a token query param instead — see the backend
  // endpoint's docstring.
  const icsHref = `${API_BASE}/calendar/lessons/me.ics?token=${encodeURIComponent(tokens.access() ?? "")}`;

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Календарь</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Уроки курса</h1>
        </div>
        <Link href={`/dashboard/courses/${id}`} className="btn btn-ghost">
          ← К курсу
        </Link>
      </header>

      {user.role === "tutor" && (
        <section className="card mt-8 p-6">
          <h2 className="display text-lg">Новый урок</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <input
              type="date"
              className="field"
              value={form.scheduled_date}
              onChange={(e) => setForm((f) => ({ ...f, scheduled_date: e.target.value }))}
            />
            <input
              type="time"
              className="field"
              value={form.scheduled_time}
              onChange={(e) => setForm((f) => ({ ...f, scheduled_time: e.target.value }))}
            />
            <input
              type="number"
              className="field"
              placeholder="Длительность, мин"
              value={form.duration_minutes}
              min={15}
              max={480}
              onChange={(e) => setForm((f) => ({ ...f, duration_minutes: Number(e.target.value) }))}
            />
            <select
              className="field"
              value={form.recurrence}
              onChange={(e) => setForm((f) => ({ ...f, recurrence: e.target.value as "none" | "weekly" }))}
            >
              <option value="none">Разовый урок</option>
              <option value="weekly">Еженедельно</option>
            </select>
            {form.recurrence === "weekly" && (
              <input
                type="number"
                className="field"
                placeholder="Сколько недель"
                value={form.recurrence_weeks}
                min={1}
                max={26}
                onChange={(e) => setForm((f) => ({ ...f, recurrence_weeks: Number(e.target.value) }))}
              />
            )}
          </div>
          {error && <p className="mt-2 text-sm text-coral-500">{error}</p>}
          <button
            className="btn btn-primary mt-4 !py-2 text-sm"
            disabled={creating}
            onClick={() => void createLesson()}
          >
            {creating ? "Создаём…" : "Создать"}
          </button>
        </section>
      )}

      <section className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="display text-lg">Уроки ({lessons.length})</h2>
          <a href={icsHref} className="text-sm font-semibold text-aurora-700">
            Скачать .ics →
          </a>
        </div>
        <ul className="mt-4 space-y-2">
          {lessons.map((l) => (
            <li key={l.id} className="card flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-semibold">{new Date(l.scheduled_start).toLocaleString("ru-RU")}</p>
                <p className="text-xs text-ink-3">
                  до{" "}
                  {new Date(l.scheduled_end).toLocaleTimeString("ru-RU", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}{" "}
                  · {l.status}
                </p>
                <div className="mt-2 flex flex-wrap gap-3 text-xs font-semibold">
                  {l.meeting_url && (
                    <a href={l.meeting_url} target="_blank" rel="noreferrer" className="text-aurora-700">
                      Войти в Zoom →
                    </a>
                  )}
                  {l.start_url && (
                    <a href={l.start_url} target="_blank" rel="noreferrer" className="text-jade-700">
                      Начать как хост →
                    </a>
                  )}
                </div>
              </div>
              {canManage && (
                <div className="flex flex-wrap gap-2">
                  {l.status === "scheduled" && (
                    <button
                      className="btn btn-ghost !py-1.5 text-xs"
                      onClick={() => void setStatus(l.id, "completed")}
                    >
                      Отметить проведённым
                    </button>
                  )}
                  <button className="btn btn-ghost !py-1.5 text-xs" onClick={() => void removeLesson(l.id)}>
                    Удалить
                  </button>
                  {l.series_id && (
                    <button
                      className="btn btn-ghost !py-1.5 text-xs text-coral-500"
                      onClick={() => void removeSeries(l.series_id as string)}
                    >
                      Удалить серию
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
          {lessons.length === 0 && <p className="card p-6 text-sm text-ink-3">Уроков пока нет.</p>}
        </ul>
      </section>
    </div>
  );
}
