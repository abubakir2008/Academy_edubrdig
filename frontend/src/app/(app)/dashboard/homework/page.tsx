"use client";

import { useCallback, useEffect, useState } from "react";

import { API_BASE, get, post, put, tokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatBishkekDate } from "@/lib/time";
import type { Homework, HomeworkStatus, Profile } from "@/lib/types";

const STATUS_LABEL: Record<HomeworkStatus, string> = {
  assigned: "Задано",
  submitted: "Сдано",
  graded: "Проверено",
};

const STATUS_TONE: Record<HomeworkStatus, string> = {
  assigned: "!bg-citrus-100 !text-citrus-700",
  submitted: "!bg-aurora-50 !text-aurora-700",
  graded: "!bg-jade-100 !text-jade-700",
};

export default function HomeworkPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<Homework[]>([]);
  const [profiles, setProfiles] = useState<Record<string, Profile>>({});
  const [error, setError] = useState<string | null>(null);

  const isTutor = user?.role === "tutor";

  const load = useCallback(async () => {
    const list = await get<Homework[]>("/calendar/homework/me", true).catch(() => [] as Homework[]);
    setItems(list);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Resolve the other side's name (student for a tutor, teacher for a
  // student) — same batched-lookup pattern as the course roster page.
  useEffect(() => {
    const ids = Array.from(
      new Set(
        items
          .map((h) => (isTutor ? h.student_id : h.teacher_id))
          .filter((id) => !(id in profiles)),
      ),
    );
    if (ids.length === 0) return;
    get<Profile[]>(`/users/batch?ids=${encodeURIComponent(ids.join(","))}`)
      .then((list) => {
        setProfiles((prev) => {
          const next = { ...prev };
          for (const p of list) next[p.user_id] = p;
          return next;
        });
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, isTutor]);

  if (!user) return null;

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Учёба</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Домашние задания</h1>
        <p className="mt-2 text-sm text-ink-3">
          {isTutor
            ? "Здесь — всё, что вы задали, и работы, которые пора проверить."
            : "Здесь — всё, что вам задали, и что пора сдать."}
        </p>
      </header>

      {error && <p className="mt-4 text-sm text-coral-500">{error}</p>}

      <ul className="mt-8 space-y-3">
        {items.map((hw) => (
          <HomeworkCard
            key={hw.id}
            hw={hw}
            isTutor={isTutor}
            peerName={profiles[isTutor ? hw.student_id : hw.teacher_id]?.full_name || "…"}
            onChanged={(updated) => setItems((prev) => prev.map((h) => (h.id === updated.id ? updated : h)))}
            onError={setError}
          />
        ))}
        {items.length === 0 && <p className="card p-6 text-sm text-ink-3">Заданий пока нет.</p>}
      </ul>
    </div>
  );
}

function HomeworkCard({
  hw,
  isTutor,
  peerName,
  onChanged,
  onError,
}: {
  hw: Homework;
  isTutor: boolean;
  peerName: string;
  onChanged: (h: Homework) => void;
  onError: (msg: string) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [note, setNote] = useState("");
  const [gradeInput, setGradeInput] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitFile(file: File) {
    setUploading(true);
    onError("");
    try {
      const form = new FormData();
      form.append("bucket", "materials");
      form.append("file", file);
      const token = tokens.access();
      const res = await fetch(`${API_BASE}/storage/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: form,
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail || "Не удалось загрузить файл");
      }
      const { url } = (await res.json()) as { url: string };
      const updated = await post<Homework>(
        `/calendar/homework/${hw.id}/submit`,
        { submission_url: `${API_BASE}${url}`, submission_note: note || undefined },
        true,
      );
      onChanged(updated);
      setNote("");
    } catch (e) {
      onError(e instanceof Error ? e.message : "Не удалось сдать работу");
    } finally {
      setUploading(false);
    }
  }

  async function submitGrade() {
    const g = Number(gradeInput);
    if (!gradeInput || Number.isNaN(g)) return;
    setBusy(true);
    onError("");
    try {
      const updated = await put<Homework>(
        `/calendar/homework/${hw.id}/grade`,
        { grade: g, comment: comment || undefined },
        true,
      );
      onChanged(updated);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Не удалось выставить оценку");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{hw.title}</p>
          <p className="text-xs text-ink-3">
            {isTutor ? "Ученик" : "Учитель"}: {peerName}
          </p>
          {hw.description && <p className="mt-1 text-sm text-ink-2">{hw.description}</p>}
          {hw.due_date && <p className="mt-1 text-xs text-ink-3">Срок: {formatBishkekDate(hw.due_date)}</p>}
        </div>
        <span className={`chip ${STATUS_TONE[hw.status]}`}>{STATUS_LABEL[hw.status]}</span>
      </div>

      {hw.submission_url && (
        <p className="mt-3 text-sm">
          <a
            href={hw.submission_url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-aurora-700 underline"
          >
            Открыть сданную работу →
          </a>
          {hw.submission_note && <span className="ml-2 text-ink-3">«{hw.submission_note}»</span>}
        </p>
      )}

      {hw.status === "graded" ? (
        <p className="mt-3 rounded-xl bg-jade-50 px-4 py-3 text-sm">
          Оценка: <span className="font-semibold">{hw.grade}</span>
          {hw.comment && <span className="ml-2 text-ink-2">— {hw.comment}</span>}
        </p>
      ) : isTutor ? (
        <div className="mt-4 flex flex-wrap items-end gap-2 border-t border-line/60 pt-4">
          <div>
            <label className="label text-xs">Оценка</label>
            <input
              type="number"
              step="0.1"
              className="field w-24"
              value={gradeInput}
              onChange={(e) => setGradeInput(e.target.value)}
            />
          </div>
          <input
            className="field min-w-[10rem] flex-1"
            placeholder="Комментарий (необязательно)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button
            className="btn btn-primary !py-2 text-sm"
            disabled={busy || !gradeInput}
            onClick={() => void submitGrade()}
          >
            {busy ? "Сохраняем…" : "Оценить"}
          </button>
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line/60 pt-4">
          <input
            type="file"
            id={`hw-file-${hw.id}`}
            className="hidden"
            onChange={(e) => e.target.files?.[0] && void submitFile(e.target.files[0])}
          />
          <label
            htmlFor={`hw-file-${hw.id}`}
            className={`btn btn-ghost cursor-pointer !py-2 text-sm ${uploading ? "pointer-events-none opacity-50" : ""}`}
          >
            {uploading ? "Загружаем…" : hw.status === "submitted" ? "Пересдать файл" : "Прикрепить и сдать"}
          </label>
          <input
            className="field min-w-[10rem] flex-1"
            placeholder="Комментарий к сдаче (необязательно)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
      )}
    </li>
  );
}
