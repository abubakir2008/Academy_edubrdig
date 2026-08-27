"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Film } from "lucide-react";

import { ApiError, API_BASE, del, get, post, put, tokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  LESSON_STATUS_CARD_CLASS,
  bishkekInputToISO,
  formatBishkekDateTime,
  formatBishkekTime,
  isLessonJoinable,
  lessonVisualStatus,
} from "@/lib/time";
import type { Lesson, LessonStatus, Recording } from "@/lib/types";

const STATUS_LABEL: Record<LessonStatus, string> = {
  scheduled: "Запланирован",
  completed: "Проведён",
  cancelled: "Отменён",
  missed: "Не состоялся",
};

const EMPTY = {
  title: "",
  description: "",
  scheduled_date: "",
  scheduled_time: "",
  duration_minutes: 60,
};

export default function CourseCalendarPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [recordingsByLesson, setRecordingsByLesson] = useState<Record<string, Recording[] | undefined>>({});
  const [playing, setPlaying] = useState<Recording | null>(null);

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
      const scheduled_start = bishkekInputToISO(form.scheduled_date, form.scheduled_time);
      await post(
        "/calendar/lessons",
        {
          course_id: id,
          scheduled_start,
          duration_minutes: form.duration_minutes,
          title: form.title || undefined,
          description: form.description || undefined,
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
    try {
      await del(`/calendar/lessons/${lessonId}`);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось удалить урок");
    }
  }

  async function removeSeries(seriesId: string) {
    try {
      await del(`/calendar/series/${seriesId}`);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось удалить серию уроков");
    }
  }

  async function toggleRecordings(lessonId: string) {
    if (expandedId === lessonId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(lessonId);
    if (recordingsByLesson[lessonId] === undefined) {
      const items = await get<Recording[]>(`/calendar/lessons/${lessonId}/recordings`, true).catch(
        () => [] as Recording[],
      );
      setRecordingsByLesson((prev) => ({ ...prev, [lessonId]: items }));
    }
  }

  async function removeRecording(lessonId: string, objectName: string) {
    if (!window.confirm("Удалить запись безвозвратно?")) return;
    try {
      await del(`/calendar/lessons/${lessonId}/recordings/${encodeURIComponent(objectName)}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось удалить запись");
      return;
    }
    setRecordingsByLesson((prev) => ({
      ...prev,
      [lessonId]: (prev[lessonId] ?? []).filter((r) => r.object_name !== objectName),
    }));
  }

  function formatDuration(seconds: number | null): string {
    if (!seconds) return "";
    const m = Math.round(seconds / 60);
    return ` · ${m} мин`;
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
              className="field sm:col-span-2"
              placeholder="Название урока (необязательно — по умолчанию «Урок»)"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
            <textarea
              className="field sm:col-span-2 min-h-20 resize-y"
              placeholder="Описание урока (необязательно)"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
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
            <select
              className="field"
              value={form.duration_minutes}
              onChange={(e) => setForm((f) => ({ ...f, duration_minutes: Number(e.target.value) }))}
            >
              <option value={30}>30 минут</option>
              <option value={60}>1 час</option>
              <option value={90}>1,5 часа</option>
              <option value={120}>2 часа</option>
            </select>
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
            <li
              key={l.id}
              className={`card flex flex-wrap items-center justify-between gap-3 p-4 ${LESSON_STATUS_CARD_CLASS[lessonVisualStatus(l)]}`}
            >
              <div>
                <p className="font-semibold">{l.title || "Урок"}</p>
                {l.description && <p className="mt-0.5 text-xs text-ink-3">{l.description}</p>}
                <p className="mt-1 text-sm">
                  {formatBishkekDateTime(l.scheduled_start)} (время Бишкека)
                </p>
                <p className="text-xs text-ink-3">
                  до {formatBishkekTime(l.scheduled_end)} · {STATUS_LABEL[l.status]}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs font-semibold">
                  {isLessonJoinable(l) ? (
                    <Link href={`/dashboard/lessons/${l.id}/call`} className="text-aurora-700">
                      Войти на урок →
                    </Link>
                  ) : (
                    <span className="font-normal text-ink-3">Вход на урок — только во время урока</span>
                  )}
                  {lessonVisualStatus(l) !== "upcoming" && (
                    <button
                      className="flex items-center gap-1 text-ink-2 hover:text-ink"
                      onClick={() => void toggleRecordings(l.id)}
                    >
                      <Film className="h-3.5 w-3.5" aria-hidden />
                      {expandedId === l.id ? "Скрыть записи" : "Записи"}
                    </button>
                  )}
                </div>
              </div>
              {canManage && (
                <div className="flex flex-wrap gap-2">
                  {(l.status === "scheduled" || l.status === "missed") && (
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
              {expandedId === l.id && (
                <div className="mt-1 w-full border-t border-line/60 pt-3">
                  {recordingsByLesson[l.id] === undefined ? (
                    <p className="text-xs text-ink-3">Загрузка…</p>
                  ) : recordingsByLesson[l.id]!.length === 0 ? (
                    <p className="text-xs text-ink-3">
                      Записей нет — либо урок ещё не прошёл, либо запись не была настроена на сервере.
                    </p>
                  ) : (
                    <ul className="space-y-2">
                      {recordingsByLesson[l.id]!.map((r) => (
                        <li key={r.object_name} className="flex flex-wrap items-center justify-between gap-2 text-xs">
                          <button
                            type="button"
                            onClick={() => setPlaying(r)}
                            className="flex items-center gap-1.5 font-semibold text-aurora-700"
                          >
                            <Film className="h-3.5 w-3.5" aria-hidden />
                            {r.started_at ? formatBishkekDateTime(r.started_at) : "Запись"}
                            {formatDuration(r.duration_seconds)}
                          </button>
                          {canManage && (
                            <button
                              className="text-coral-500"
                              onClick={() => void removeRecording(l.id, r.object_name)}
                            >
                              Удалить
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </li>
          ))}
          {lessons.length === 0 && <p className="card p-6 text-sm text-ink-3">Уроков пока нет.</p>}
        </ul>
      </section>

      {playing && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/90 p-4"
          onClick={() => setPlaying(null)}
        >
          <div className="w-full max-w-4xl" onClick={(e) => e.stopPropagation()}>
            <div className="mb-2 flex items-center justify-between text-sm text-white">
              <span>
                {playing.started_at ? formatBishkekDateTime(playing.started_at) : "Запись"}
                {formatDuration(playing.duration_seconds)}
              </span>
              <button type="button" className="btn btn-ghost !py-1.5 text-xs" onClick={() => setPlaying(null)}>
                Закрыть ✕
              </button>
            </div>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video
              key={playing.object_name}
              src={playing.url}
              controls
              autoPlay
              className="max-h-[80vh] w-full rounded-xl bg-black"
            />
          </div>
        </div>
      )}
    </div>
  );
}
