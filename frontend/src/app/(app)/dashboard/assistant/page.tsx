"use client";

import { useState } from "react";

import { MarkdownLite } from "@/components/markdown-lite";
import { ApiError, post } from "@/lib/api";
import type { AiHomeworkPlan, AiLessonAnalysis, AiProgressAnalysis, AiSource, AiTopicExplanation } from "@/lib/types";

const SOURCE_LABEL: Record<AiSource, string> = {
  anthropic: "Ответ модели (Claude)",
  gemini: "Ответ модели (Gemini)",
  template: "ИИ не настроен на сервере — это заготовка, не настоящий ответ",
  rules: "Правило, без модели",
};

type Tool = "explain" | "homework" | "lesson" | "progress";

const TOOLS: { id: Tool; label: string }[] = [
  { id: "explain", label: "Объяснить тему" },
  { id: "homework", label: "Задания от ИИ" },
  { id: "lesson", label: "Разбор урока" },
  { id: "progress", label: "Мой прогресс" },
];

function SourceNote({ source }: { source: AiSource }) {
  return (
    <p className={`mt-3 text-xs ${source === "template" ? "text-coral-500" : "text-ink-3"}`}>
      {SOURCE_LABEL[source]}
    </p>
  );
}

async function runAi<T>(path: string, body: unknown, onError: (m: string) => void): Promise<T | null> {
  try {
    return await post<T>(path, body, true);
  } catch (e) {
    onError(
      e instanceof ApiError && e.status === 429
        ? "Дневной лимит запросов к ИИ исчерпан — попробуйте завтра."
        : e instanceof Error
          ? e.message
          : "Не удалось получить ответ",
    );
    return null;
  }
}

export default function AssistantPage() {
  const [tool, setTool] = useState<Tool>("explain");

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Помощник</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">ИИ-помощник</h1>
        <p className="mt-2 text-sm text-ink-3">
          Объясняет тему, придумывает задания, разбирает конспект урока — под каждым ответом видно,
          настоящая это модель или заготовка на случай, если ИИ ещё не подключен на сервере.
        </p>
      </header>

      <div className="mt-6 flex flex-wrap gap-2">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            className={`chip ${tool === t.id ? "!border-aurora-600 !bg-aurora-50 !text-aurora-700" : ""}`}
            onClick={() => setTool(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tool === "explain" && <ExplainTopic />}
        {tool === "homework" && <GenerateHomework />}
        {tool === "lesson" && <AnalyzeLesson />}
        {tool === "progress" && <AnalyzeProgress />}
      </div>
    </div>
  );
}

function ExplainTopic() {
  const [subject, setSubject] = useState("");
  const [level, setLevel] = useState("beginner");
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AiTopicExplanation | null>(null);

  async function run() {
    if (!subject.trim() || !topic.trim()) return;
    setBusy(true);
    setError(null);
    setResult(await runAi<AiTopicExplanation>("/ai/topic/explain", { subject, level, topic }, setError));
    setBusy(false);
  }

  return (
    <section className="card p-6">
      <div className="grid gap-3 sm:grid-cols-3">
        <input className="field" placeholder="Предмет" value={subject} onChange={(e) => setSubject(e.target.value)} />
        <input className="field" placeholder="Тема" value={topic} onChange={(e) => setTopic(e.target.value)} />
        <select className="field" value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="beginner">Начальный</option>
          <option value="intermediate">Средний</option>
          <option value="advanced">Продвинутый</option>
        </select>
      </div>
      {error && <p className="mt-3 text-sm text-coral-500">{error}</p>}
      <button className="btn btn-primary mt-4 !py-2 text-sm" disabled={busy} onClick={() => void run()}>
        {busy ? "Спрашиваем…" : "Объяснить"}
      </button>
      {result && (
        <div className="mt-6 border-t border-line/60 pt-5">
          <MarkdownLite text={result.content} />
          <SourceNote source={result.source} />
        </div>
      )}
    </section>
  );
}

function GenerateHomework() {
  const [subject, setSubject] = useState("");
  const [level, setLevel] = useState("beginner");
  const [topic, setTopic] = useState("");
  const [numTasks, setNumTasks] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AiHomeworkPlan | null>(null);

  async function run() {
    if (!subject.trim() || !topic.trim()) return;
    setBusy(true);
    setError(null);
    setResult(
      await runAi<AiHomeworkPlan>(
        "/ai/homework/generate",
        { subject, level, topic, num_tasks: numTasks },
        setError,
      ),
    );
    setBusy(false);
  }

  return (
    <section className="card p-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <input className="field" placeholder="Предмет" value={subject} onChange={(e) => setSubject(e.target.value)} />
        <input className="field" placeholder="Тема" value={topic} onChange={(e) => setTopic(e.target.value)} />
        <select className="field" value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="beginner">Начальный</option>
          <option value="intermediate">Средний</option>
          <option value="advanced">Продвинутый</option>
        </select>
        <select className="field" value={numTasks} onChange={(e) => setNumTasks(Number(e.target.value))}>
          {[1, 2, 3, 5, 8, 10].map((n) => (
            <option key={n} value={n}>
              {n} заданий
            </option>
          ))}
        </select>
      </div>
      {error && <p className="mt-3 text-sm text-coral-500">{error}</p>}
      <button className="btn btn-primary mt-4 !py-2 text-sm" disabled={busy} onClick={() => void run()}>
        {busy ? "Придумываем…" : "Сгенерировать"}
      </button>
      {result && (
        <div className="mt-6 border-t border-line/60 pt-5">
          <p className="text-xs text-ink-3">≈ {result.estimated_minutes} мин</p>
          <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm text-ink-2">
            {result.tasks.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ol>
          <SourceNote source={result.source} />
        </div>
      )}
    </section>
  );
}

function AnalyzeLesson() {
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AiLessonAnalysis | null>(null);

  async function run() {
    if (!notes.trim()) return;
    setBusy(true);
    setError(null);
    setResult(await runAi<AiLessonAnalysis>("/ai/lesson/analyze", { notes }, setError));
    setBusy(false);
  }

  return (
    <section className="card p-6">
      <textarea
        className="field min-h-32 w-full resize-y"
        placeholder="Вставьте конспект или заметки с урока…"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      {error && <p className="mt-3 text-sm text-coral-500">{error}</p>}
      <button className="btn btn-primary mt-4 !py-2 text-sm" disabled={busy} onClick={() => void run()}>
        {busy ? "Разбираем…" : "Разобрать"}
      </button>
      {result && (
        <div className="mt-6 border-t border-line/60 pt-5">
          <p className="text-sm text-ink-2">{result.summary}</p>
          {result.key_points.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-2">
              {result.key_points.map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          )}
          <SourceNote source={result.source} />
        </div>
      )}
    </section>
  );
}

function AnalyzeProgress() {
  const [lessons, setLessons] = useState(0);
  const [hours, setHours] = useState(0);
  const [rating, setRating] = useState(5);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AiProgressAnalysis | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setResult(
      await runAi<AiProgressAnalysis>(
        "/ai/progress/analyze",
        { lessons_completed: lessons, hours_spent: hours, avg_rating: rating },
        setError,
      ),
    );
    setBusy(false);
  }

  return (
    <section className="card p-6">
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label className="label text-xs">Уроков пройдено</label>
          <input
            type="number"
            min={0}
            className="field"
            value={lessons}
            onChange={(e) => setLessons(Number(e.target.value))}
          />
        </div>
        <div>
          <label className="label text-xs">Часов занятий</label>
          <input
            type="number"
            min={0}
            className="field"
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
          />
        </div>
        <div>
          <label className="label text-xs">Средняя оценка (0-5)</label>
          <input
            type="number"
            min={0}
            max={5}
            step={0.1}
            className="field"
            value={rating}
            onChange={(e) => setRating(Number(e.target.value))}
          />
        </div>
      </div>
      {error && <p className="mt-3 text-sm text-coral-500">{error}</p>}
      <button className="btn btn-primary mt-4 !py-2 text-sm" disabled={busy} onClick={() => void run()}>
        {busy ? "Считаем…" : "Проанализировать"}
      </button>
      {result && (
        <div className="mt-6 border-t border-line/60 pt-5">
          <p className="text-sm">
            Уровень: <span className="font-semibold">{result.level}</span>
          </p>
          <p className="mt-2 text-sm text-ink-2">{result.recommendation}</p>
          <SourceNote source={result.source} />
        </div>
      )}
    </section>
  );
}
