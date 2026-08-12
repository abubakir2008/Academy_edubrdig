"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { ApiError, post } from "@/lib/api";
import {
  AMERICA_COUNTRIES,
  EUROPE_COUNTRIES,
  GOALS,
  SUBJECT_GROUPS,
  emptyLeadForm,
  type LeadForm,
  type Option,
} from "@/lib/onboarding";

const STEP_TITLES = ["Что учите", "Зачем", "Дата рождения", "Где учитесь", "Переезд", "Контакты"];
const TOTAL_STEPS = STEP_TITLES.length;

/**
 * A fixed six-step intake form, not a filter: it ends by collecting a name
 * and a contact, so staff can follow up even with visitors who have no
 * account yet — this platform has no self-registration. Posts to the public
 * `POST /leads` (backoffice); staff review submissions under
 * `/dashboard/leads`. Also the destination for "Оставить заявку" on a
 * tutor's public card/profile (?tutor=<id>&name=<name>) — one shared intake
 * form/pipeline instead of a separate per-tutor one.
 */
export function OnboardingWizard() {
  const params = useSearchParams();
  const tutorId = params.get("tutor");
  const tutorName = params.get("name");
  const [index, setIndex] = useState(0);
  const [form, setForm] = useState<LeadForm>(emptyLeadForm);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(patch: Partial<LeadForm>, advance = false) {
    setForm((f) => ({ ...f, ...patch }));
    if (advance) setTimeout(() => setIndex((i) => Math.min(i + 1, TOTAL_STEPS - 1)), 180);
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await post(
        "/leads",
        {
          subject: form.subject || null,
          goal: form.goal || null,
          date_of_birth: form.date_of_birth || null,
          study_place: form.study_place || null,
          destination_country: form.destination_country || null,
          full_name: form.full_name.trim(),
          contact_phone: form.contact_phone.trim() || null,
          contact_email: form.contact_email.trim() || null,
          preferred_tutor_id: tutorId || null,
        },
        false,
      );
      setSubmitted(true);
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) {
        // Same phone/email submitted a request within the last 24h — the
        // backend rejects the write outright rather than silently duplicating it.
        setError("Заявка с этим номером или почтой уже отправлена недавно — мы уже скоро свяжемся с вами.");
      } else {
        setError(e instanceof ApiError ? e.message : "Не удалось отправить заявку. Попробуйте ещё раз.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) return <ThankYou />;

  const progress = Math.round((index / (TOTAL_STEPS - 1)) * 100);
  const canAdvance = [
    Boolean(form.subject),
    Boolean(form.goal),
    Boolean(form.date_of_birth),
    Boolean(form.study_place?.trim()),
    false,
  ][index];
  const isLast = index === TOTAL_STEPS - 1;
  const canSubmit = form.full_name.trim().length > 0 && (form.contact_phone.trim() || form.contact_email.trim());

  return (
    <div className="mx-auto grid max-w-6xl gap-10 px-5 py-10 lg:grid-cols-[260px_1fr] lg:py-16">
      <aside className="lg:sticky lg:top-28 lg:self-start">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Заявка</p>
        <h1 className="display mt-2 text-2xl">
          Шаг {index + 1} из {TOTAL_STEPS}
        </h1>
        {tutorId && (
          <p className="mt-2 text-sm text-ink-3">
            Репетитору{tutorName ? ` ${tutorName}` : ""}
          </p>
        )}

        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-line">
          <div
            className="h-full rounded-full bg-aurora-600 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        <ol className="mt-6 hidden space-y-1.5 lg:block">
          {STEP_TITLES.map((title, i) => (
            <li key={title} className="flex items-center gap-2.5 rounded-xl px-2.5 py-1.5 text-sm">
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] ${
                  i < index ? "bg-jade-500 text-white" : i === index ? "bg-aurora-600 text-white" : "bg-line text-ink-3"
                }`}
              >
                {i < index ? "✓" : i + 1}
              </span>
              <span className={i === index ? "font-semibold text-aurora-700" : "text-ink-3"}>{title}</span>
            </li>
          ))}
        </ol>
      </aside>

      <section key={index} className="animate-rise">
        {index === 0 && (
          <Step title="Что вы хотите изучать?" subtitle="Выберите направление — дальше пара вопросов, и мы свяжемся с вами">
            {SUBJECT_GROUPS.map((group) => (
              <div key={group.id} className="mt-6 first:mt-0">
                <p className="mb-2 text-sm font-semibold text-ink-3">
                  {group.emoji} {group.label}
                </p>
                <ChoiceGrid
                  options={group.subjects}
                  selected={form.subject}
                  onPick={(label) => update({ subject: label }, true)}
                />
              </div>
            ))}
          </Step>
        )}

        {index === 1 && (
          <Step title="Для чего?" subtitle="Так мы сразу подберём подходящий курс">
            <ChoiceGrid options={GOALS} selected={form.goal} onPick={(label) => update({ goal: label }, true)} />
          </Step>
        )}

        {index === 2 && (
          <Step title="Дата рождения" subtitle="Понадобится, чтобы подобрать программу по возрасту">
            <input
              type="date"
              className="field max-w-xs"
              value={form.date_of_birth ?? ""}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(e) => update({ date_of_birth: e.target.value })}
            />
          </Step>
        )}

        {index === 3 && (
          <Step title="Где вы учитесь?" subtitle="Вуз, колледж или школа">
            <input
              type="text"
              className="field max-w-md"
              placeholder="Например: КНУ им. Ж. Баласагына"
              value={form.study_place ?? ""}
              onChange={(e) => update({ study_place: e.target.value })}
              autoFocus
            />
          </Step>
        )}

        {index === 4 && (
          <Step title="Хотите переехать в другую страну?" subtitle="Необязательно — этот шаг можно пропустить">
            <p className="mb-2 text-sm font-semibold text-ink-3">Европа</p>
            <ChoiceGrid
              options={EUROPE_COUNTRIES.map((c) => ({ id: c, label: c }))}
              selected={form.destination_country}
              onPick={(label) => update({ destination_country: label })}
            />
            <p className="mb-2 mt-6 text-sm font-semibold text-ink-3">Америка</p>
            <ChoiceGrid
              options={AMERICA_COUNTRIES.map((c) => ({ id: c, label: c }))}
              selected={form.destination_country}
              onPick={(label) => update({ destination_country: label })}
            />
          </Step>
        )}

        {index === 5 && (
          <Step title="Как с вами связаться?" subtitle="Оставьте имя и телефон или почту — мы подберём курс и свяжемся">
            <div className="max-w-md space-y-4">
              <div>
                <label className="label">Имя</label>
                <input
                  type="text"
                  className="field"
                  value={form.full_name}
                  onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                />
              </div>
              <div>
                <label className="label">Телефон</label>
                <input
                  type="tel"
                  className="field"
                  placeholder="+996 700 000 000"
                  value={form.contact_phone}
                  onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))}
                />
              </div>
              <div>
                <label className="label">Email</label>
                <input
                  type="email"
                  className="field"
                  placeholder="you@example.com"
                  value={form.contact_email}
                  onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                />
              </div>
              <p className="text-xs text-ink-3">Укажите хотя бы один способ связи — телефон или почту.</p>
              {error && <p className="text-sm text-coral-500">{error}</p>}
            </div>
          </Step>
        )}

        <div className="mt-10 flex flex-wrap items-center gap-3">
          <button className="btn btn-ghost" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>
            Назад
          </button>

          {isLast ? (
            <button className="btn btn-primary" onClick={() => void submit()} disabled={!canSubmit || submitting}>
              {submitting ? "Отправляем…" : "Отправить заявку"}
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={() => setIndex((i) => Math.min(i + 1, TOTAL_STEPS - 1))}
              disabled={!canAdvance}
            >
              Далее
            </button>
          )}

          {index === 4 && !isLast && (
            <button
              type="button"
              className="text-sm font-semibold text-ink-3 hover:text-ink"
              onClick={() => {
                update({ destination_country: undefined });
                setIndex((i) => Math.min(i + 1, TOTAL_STEPS - 1));
              }}
            >
              Пропустить
            </button>
          )}
        </div>
      </section>
    </div>
  );
}

/* ------------------------------ Pieces --------------------------------- */

function Step({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <>
      <h2 className="display text-[clamp(1.7rem,3.6vw,2.5rem)]">{title}</h2>
      {subtitle && <p className="mt-3 max-w-xl text-ink-3">{subtitle}</p>}
      <div className="mt-8">{children}</div>
    </>
  );
}

function ChoiceGrid({
  options,
  selected,
  onPick,
}: {
  options: Option[];
  selected?: string;
  onPick: (label: string) => void;
}) {
  if (!options.length) return <p className="text-sm text-ink-3">Список пока пуст.</p>;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {options.map((option) => {
        const active = selected === option.label;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={active}
            onClick={() => onPick(option.label)}
            className={`card flex items-start gap-3 p-4 text-left transition-all hover:-translate-y-0.5 hover:border-aurora-300 hover:shadow-lift ${
              active ? "border-aurora-600! bg-aurora-50 shadow-lift" : ""
            }`}
          >
            {option.emoji ? (
              <span className="text-2xl leading-none" aria-hidden>
                {option.emoji}
              </span>
            ) : (
              <span
                aria-hidden
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 text-[11px] ${
                  active ? "border-aurora-600 bg-aurora-600 text-white" : "border-line"
                }`}
              >
                {active ? "✓" : ""}
              </span>
            )}
            <span className="min-w-0">
              <span className="block font-semibold">{option.label}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ThankYou() {
  return (
    <div className="mx-auto max-w-xl px-5 py-24 text-center">
      <span className="text-4xl" aria-hidden>
        ✅
      </span>
      <h1 className="display mt-4 text-[clamp(1.8rem,4vw,2.6rem)]">Спасибо! Заявка отправлена</h1>
      <p className="mt-4 text-ink-3">
        Мы посмотрим ваши ответы и свяжемся по указанному телефону или почте, чтобы подобрать курс.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link href="/" className="btn btn-primary">
          На главную
        </Link>
        <Link href="/login" className="btn btn-ghost">
          Уже есть доступ? Войти
        </Link>
      </div>
    </div>
  );
}
