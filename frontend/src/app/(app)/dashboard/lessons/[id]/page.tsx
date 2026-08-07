"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { get, post, put } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Homework, Lesson } from "@/lib/types";

const STATUS: Record<string, { label: string; tone: string }> = {
  scheduled: { label: "Запланирован", tone: "!bg-citrus-100 !text-citrus-700" },
  in_progress: { label: "Идёт сейчас", tone: "!bg-jade-100 !text-jade-700" },
  completed: { label: "Завершён", tone: "!bg-aurora-50 !text-aurora-700" },
  cancelled: { label: "Отменён", tone: "!bg-coral-100 !text-coral-500" },
};

const HW_STATUS: Record<string, { label: string; tone: string }> = {
  pending: { label: "Ждёт выполнения", tone: "!bg-citrus-100 !text-citrus-700" },
  submitted: { label: "На проверке", tone: "!bg-aurora-50 !text-aurora-700" },
  graded: { label: "Оценено", tone: "!bg-jade-100 !text-jade-700" },
};

export default function LessonPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [busy, setBusy] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [myNotes, setMyNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [recordingUrl, setRecordingUrl] = useState("");
  const [savingRecording, setSavingRecording] = useState(false);

  const [hwForm, setHwForm] = useState({ title: "", description: "" });
  const [addingHw, setAddingHw] = useState(false);
  const [submissions, setSubmissions] = useState<Record<string, string>>({});
  const [grades, setGrades] = useState<Record<string, { grade: string; feedback: string }>>({});
  const [hwBusy, setHwBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const l = await get<Lesson>(`/lessons/${id}`, true);
      setLesson(l);
      setRecordingUrl(l.recording_url ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить урок");
    } finally {
      setBusy(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!user || busy) return <div className="mx-auto max-w-3xl px-5 py-12" />;
  if (!lesson) {
    return (
      <div className="mx-auto max-w-3xl px-5 py-12 text-sm text-coral-500">
        {error ?? "Урок не найден"}
      </div>
    );
  }

  const isTutor = user.id === lesson.tutor_id;
  const myNotesValue = myNotes || (isTutor ? lesson.tutor_notes : lesson.student_notes) || "";
  const partnerNotes = isTutor ? lesson.student_notes : lesson.tutor_notes;
  const status = STATUS[lesson.status] ?? { label: lesson.status, tone: "" };

  async function act(action: "start" | "complete") {
    setActing(true);
    setError(null);
    try {
      const updated = await post<Lesson>(`/lessons/${id}/${action}`, undefined, true);
      setLesson(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось выполнить действие");
    } finally {
      setActing(false);
    }
  }

  async function saveNotes() {
    setSavingNotes(true);
    setError(null);
    try {
      const updated = await put<Lesson>(
        `/lessons/${id}/notes`,
        isTutor ? { tutor_notes: myNotesValue } : { student_notes: myNotesValue },
        true,
      );
      setLesson(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить заметки");
    } finally {
      setSavingNotes(false);
    }
  }

  async function saveRecording() {
    setSavingRecording(true);
    setError(null);
    try {
      const updated = await put<Lesson>(`/lessons/${id}/recording`, { recording_url: recordingUrl }, true);
      setLesson(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить ссылку на запись");
    } finally {
      setSavingRecording(false);
    }
  }

  async function assignHomework() {
    if (!hwForm.title.trim()) return;
    setAddingHw(true);
    setError(null);
    try {
      const hw = await post<Homework>(
        `/lessons/${id}/homework`,
        { title: hwForm.title, description: hwForm.description || null },
        true,
      );
      setLesson((l) => (l ? { ...l, homeworks: [...l.homeworks, hw] } : l));
      setHwForm({ title: "", description: "" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось задать домашку");
    } finally {
      setAddingHw(false);
    }
  }

  async function submitHomework(hwId: string) {
    const text = submissions[hwId];
    if (!text?.trim()) return;
    setHwBusy(hwId);
    setError(null);
    try {
      const hw = await post<Homework>(`/lessons/homework/${hwId}/submit`, { submission_text: text }, true);
      setLesson((l) => (l ? { ...l, homeworks: l.homeworks.map((h) => (h.id === hwId ? hw : h)) } : l));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отправить решение");
    } finally {
      setHwBusy(null);
    }
  }

  async function gradeHomework(hwId: string) {
    const g = grades[hwId];
    if (!g?.grade?.trim()) return;
    setHwBusy(hwId);
    setError(null);
    try {
      const hw = await post<Homework>(
        `/lessons/homework/${hwId}/grade`,
        { grade: g.grade, feedback: g.feedback || null },
        true,
      );
      setLesson((l) => (l ? { ...l, homeworks: l.homeworks.map((h) => (h.id === hwId ? hw : h)) } : l));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось выставить оценку");
    } finally {
      setHwBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Урок</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">
            {lesson.subject || "Занятие"}
          </h1>
          <p className="mt-2 text-sm text-ink-3">
            {new Date(lesson.scheduled_start).toLocaleString("ru-RU", { dateStyle: "long", timeStyle: "short" })} ·{" "}
            {lesson.duration_minutes} мин
          </p>
        </div>
        <span className={`chip ${status.tone}`}>{status.label}</span>
      </header>

      {error && <p className="card mt-4 border-coral-500/40 bg-coral-100 p-4 text-sm">{error}</p>}

      <section className="card mt-8 flex flex-wrap gap-2 p-6">
        {lesson.status === "scheduled" && (
          <button className="btn btn-primary !py-2.5 text-sm" disabled={acting} onClick={() => void act("start")}>
            {acting ? "…" : "Начать урок"}
          </button>
        )}
        {lesson.status === "in_progress" && (
          <button className="btn btn-primary !py-2.5 text-sm" disabled={acting} onClick={() => void act("complete")}>
            {acting ? "…" : "Завершить урок"}
          </button>
        )}
        {lesson.status !== "scheduled" && lesson.status !== "in_progress" && (
          <p className="text-sm text-ink-3">Урок {status.label.toLowerCase()}.</p>
        )}
      </section>

      <section className="card mt-6 space-y-3 p-6">
        <h2 className="display text-lg">Заметки</h2>
        <div>
          <label className="label">{isTutor ? "Ваши заметки (видны только вам)" : "Ваши заметки"}</label>
          <textarea
            className="field min-h-24 resize-y text-sm"
            value={myNotesValue}
            onChange={(e) => setMyNotes(e.target.value)}
          />
          <button
            className="btn btn-ghost mt-2 !py-1.5 text-xs"
            disabled={savingNotes}
            onClick={() => void saveNotes()}
          >
            {savingNotes ? "Сохраняем…" : "Сохранить"}
          </button>
        </div>
        {partnerNotes && (
          <div>
            <label className="label">{isTutor ? "Заметки студента" : "Заметки репетитора"}</label>
            <p className="rounded-xl bg-paper-2 p-3 text-sm text-ink-2 whitespace-pre-line">{partnerNotes}</p>
          </div>
        )}
      </section>

      {isTutor ? (
        <section className="card mt-6 space-y-3 p-6">
          <h2 className="display text-lg">Запись урока</h2>
          <input
            className="field"
            placeholder="Ссылка на запись"
            value={recordingUrl}
            onChange={(e) => setRecordingUrl(e.target.value)}
          />
          <button
            className="btn btn-ghost !py-1.5 text-xs"
            disabled={savingRecording}
            onClick={() => void saveRecording()}
          >
            {savingRecording ? "Сохраняем…" : "Сохранить ссылку"}
          </button>
        </section>
      ) : (
        lesson.recording_url && (
          <section className="card mt-6 p-6">
            <h2 className="display text-lg">Запись урока</h2>
            <a href={lesson.recording_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm font-semibold text-aurora-700">
              Открыть запись →
            </a>
          </section>
        )
      )}

      <section className="card mt-6 space-y-4 p-6">
        <h2 className="display text-lg">Домашнее задание</h2>

        {lesson.homeworks.length > 0 && (
          <ul className="space-y-3">
            {lesson.homeworks.map((hw) => {
              const s = HW_STATUS[hw.status] ?? { label: hw.status, tone: "" };
              return (
                <li key={hw.id} className="rounded-xl border border-line p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold">{hw.title}</p>
                    <span className={`chip text-xs ${s.tone}`}>{s.label}</span>
                  </div>
                  {hw.description && <p className="mt-1 text-sm text-ink-3">{hw.description}</p>}

                  {hw.submission_text && (
                    <p className="mt-2 rounded-lg bg-paper-2 p-2 text-sm">
                      <b className="font-semibold">Ответ: </b>
                      {hw.submission_text}
                    </p>
                  )}
                  {hw.grade && (
                    <p className="mt-2 text-sm text-jade-700">
                      Оценка: <b>{hw.grade}</b>
                      {hw.feedback && ` — ${hw.feedback}`}
                    </p>
                  )}

                  {!isTutor && hw.status === "pending" && (
                    <div className="mt-3 space-y-2">
                      <textarea
                        className="field min-h-16 resize-y text-sm"
                        placeholder="Ваш ответ"
                        value={submissions[hw.id] ?? ""}
                        onChange={(e) => setSubmissions((s2) => ({ ...s2, [hw.id]: e.target.value }))}
                      />
                      <button
                        className="btn btn-primary !py-1.5 text-xs"
                        disabled={hwBusy === hw.id}
                        onClick={() => void submitHomework(hw.id)}
                      >
                        {hwBusy === hw.id ? "Отправляем…" : "Отправить"}
                      </button>
                    </div>
                  )}

                  {isTutor && hw.status === "submitted" && (
                    <div className="mt-3 grid gap-2 sm:grid-cols-[100px_1fr_auto]">
                      <input
                        className="field text-sm"
                        placeholder="Оценка"
                        value={grades[hw.id]?.grade ?? ""}
                        onChange={(e) =>
                          setGrades((g) => ({ ...g, [hw.id]: { ...g[hw.id], grade: e.target.value, feedback: g[hw.id]?.feedback ?? "" } }))
                        }
                      />
                      <input
                        className="field text-sm"
                        placeholder="Комментарий (необязательно)"
                        value={grades[hw.id]?.feedback ?? ""}
                        onChange={(e) =>
                          setGrades((g) => ({ ...g, [hw.id]: { grade: g[hw.id]?.grade ?? "", feedback: e.target.value } }))
                        }
                      />
                      <button
                        className="btn btn-primary !py-1.5 text-xs"
                        disabled={hwBusy === hw.id}
                        onClick={() => void gradeHomework(hw.id)}
                      >
                        {hwBusy === hw.id ? "…" : "Оценить"}
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {isTutor && (
          <div className="space-y-2 border-t border-line pt-4">
            <input
              className="field"
              placeholder="Название задания"
              value={hwForm.title}
              onChange={(e) => setHwForm((f) => ({ ...f, title: e.target.value }))}
            />
            <textarea
              className="field min-h-16 resize-y text-sm"
              placeholder="Описание (необязательно)"
              value={hwForm.description}
              onChange={(e) => setHwForm((f) => ({ ...f, description: e.target.value }))}
            />
            <button className="btn btn-ghost !py-2 text-sm" disabled={addingHw} onClick={() => void assignHomework()}>
              {addingHw ? "Добавляем…" : "+ Задать домашку"}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
