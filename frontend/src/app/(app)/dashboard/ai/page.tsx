"use client";

import { useState } from "react";

import { post } from "@/lib/api";
import { MarkdownLite } from "@/components/markdown-lite";

type Source = "template" | "anthropic" | "gemini";

type TopicExplanation = {
  subject: string;
  level: string;
  topic: string;
  content: string;
  source: Source;
};

type Homework = {
  subject: string;
  level: string;
  topic: string;
  tasks: string[];
  estimated_minutes: number;
  source: Source;
};

type LessonAnalysis = {
  word_count: number;
  sentence_count: number;
  key_points: string[];
  summary: string;
  source: Source;
};

const MODEL_LABEL: Record<Exclude<Source, "template">, string> = {
  anthropic: "✨ Ответ модели Claude",
  gemini: "✨ Ответ модели Gemini",
};

function SourceBadge({ source }: { source: Source }) {
  return source !== "template" ? (
    <span className="chip !bg-aurora-50 !text-aurora-700 text-xs">{MODEL_LABEL[source]}</span>
  ) : (
    <span
      className="chip !bg-citrus-100 !text-citrus-700 text-xs"
      title="На сервере не задан ни ANTHROPIC_API_KEY, ни GEMINI_API_KEY (или запрос к модели не удался) — ответ собран по фиксированному шаблону, без AI"
    >
      Шаблон (без AI)
    </span>
  );
}

export default function AiPage() {
  const [explainSubject, setExplainSubject] = useState("Программирование");
  const [explainLevel, setExplainLevel] = useState("beginner");
  const [explainTopic, setExplainTopic] = useState("");
  const [explanation, setExplanation] = useState<TopicExplanation | null>(null);
  const [busyExplain, setBusyExplain] = useState(false);

  const [subject, setSubject] = useState("English");
  const [level, setLevel] = useState("beginner");
  const [topic, setTopic] = useState("");
  const [numTasks, setNumTasks] = useState(3);
  const [homework, setHomework] = useState<Homework | null>(null);
  const [busyHomework, setBusyHomework] = useState(false);

  const [notes, setNotes] = useState("");
  const [analysis, setAnalysis] = useState<LessonAnalysis | null>(null);
  const [busyAnalysis, setBusyAnalysis] = useState(false);

  const [error, setError] = useState<string | null>(null);

  async function explainTopicSubmit() {
    if (!explainTopic.trim()) {
      setError("Укажите тему");
      return;
    }
    setBusyExplain(true);
    setError(null);
    try {
      setExplanation(
        await post<TopicExplanation>(
          "/ai/topic/explain",
          { subject: explainSubject, level: explainLevel, topic: explainTopic },
          true,
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось объяснить тему");
    } finally {
      setBusyExplain(false);
    }
  }

  async function generate() {
    if (!topic.trim()) {
      setError("Укажите тему");
      return;
    }
    setBusyHomework(true);
    setError(null);
    try {
      setHomework(await post<Homework>("/ai/homework/generate", { subject, level, topic, num_tasks: numTasks }, true));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сгенерировать задание");
    } finally {
      setBusyHomework(false);
    }
  }

  async function analyze() {
    if (!notes.trim()) {
      setError("Вставьте заметки урока");
      return;
    }
    setBusyAnalysis(true);
    setError(null);
    try {
      setAnalysis(await post<LessonAnalysis>("/ai/lesson/analyze", { notes }, true));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось проанализировать заметки");
    } finally {
      setBusyAnalysis(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">AI-помощник</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Объяснения, домашка и разбор урока</h1>
        <p className="mt-2 text-sm text-ink-3">
          Каждый ответ помечен честно: сгенерирован ли он моделью Claude или собран из готового шаблона —
          зависит от того, настроен ли AI-ключ на сервере.
        </p>
      </header>

      {error && <p className="card mt-4 border-coral-500/40 bg-coral-100 p-4 text-sm">{error}</p>}

      <section className="card mt-8 space-y-4 p-6">
        <h2 className="display text-lg">Объяснить тему</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Предмет</label>
            <input className="field" value={explainSubject} onChange={(e) => setExplainSubject(e.target.value)} />
          </div>
          <div>
            <label className="label">Уровень</label>
            <select className="field" value={explainLevel} onChange={(e) => setExplainLevel(e.target.value)}>
              <option value="beginner">Начальный</option>
              <option value="intermediate">Средний</option>
              <option value="advanced">Продвинутый</option>
            </select>
          </div>
        </div>
        <div>
          <label className="label">Тема</label>
          <input
            className="field"
            placeholder="напр. Массивы"
            value={explainTopic}
            onChange={(e) => setExplainTopic(e.target.value)}
          />
        </div>
        <button
          className="btn btn-primary !py-2.5 text-sm"
          disabled={busyExplain}
          onClick={() => void explainTopicSubmit()}
        >
          {busyExplain ? "Готовим объяснение…" : "Объяснить"}
        </button>

        {explanation && (
          <div className="mt-4 border-t border-line pt-4">
            <div className="mb-3 flex items-center justify-end">
              <SourceBadge source={explanation.source} />
            </div>
            <MarkdownLite text={explanation.content} />
          </div>
        )}
      </section>

      <section className="card mt-6 space-y-4 p-6">
        <h2 className="display text-lg">Сгенерировать домашнее задание</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label">Предмет</label>
            <input className="field" value={subject} onChange={(e) => setSubject(e.target.value)} />
          </div>
          <div>
            <label className="label">Уровень</label>
            <select className="field" value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="beginner">Начальный</option>
              <option value="intermediate">Средний</option>
              <option value="advanced">Продвинутый</option>
            </select>
          </div>
        </div>
        <div>
          <label className="label">Тема</label>
          <input
            className="field"
            placeholder="напр. Past Simple"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </div>
        <div>
          <label className="label">Количество заданий</label>
          <input
            className="field !w-24"
            type="number"
            min={1}
            max={10}
            value={numTasks}
            onChange={(e) => setNumTasks(Number(e.target.value))}
          />
        </div>
        <button className="btn btn-primary !py-2.5 text-sm" disabled={busyHomework} onClick={() => void generate()}>
          {busyHomework ? "Генерируем…" : "Сгенерировать"}
        </button>

        {homework && (
          <div className="mt-4 border-t border-line pt-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">≈ {homework.estimated_minutes} мин</p>
              <SourceBadge source={homework.source} />
            </div>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
              {homework.tasks.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ol>
          </div>
        )}
      </section>

      <section className="card mt-6 space-y-4 p-6">
        <h2 className="display text-lg">Разбор заметок с урока</h2>
        <textarea
          className="field min-h-28 resize-y"
          placeholder="Вставьте заметки, которые оставил репетитор после урока"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <button className="btn btn-primary !py-2.5 text-sm" disabled={busyAnalysis} onClick={() => void analyze()}>
          {busyAnalysis ? "Анализируем…" : "Разобрать"}
        </button>

        {analysis && (
          <div className="mt-4 border-t border-line pt-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-ink-3">
                {analysis.word_count} слов · {analysis.sentence_count} предложений
              </p>
              <SourceBadge source={analysis.source} />
            </div>
            {analysis.summary && <p className="mt-2 text-sm font-medium">{analysis.summary}</p>}
            {analysis.key_points.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                {analysis.key_points.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
