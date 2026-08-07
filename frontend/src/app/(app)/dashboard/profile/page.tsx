"use client";

import { useCallback, useEffect, useState } from "react";

import { del, get, post, put } from "@/lib/api";
import { CATEGORIES } from "@/lib/catalog";
import { useAuth } from "@/lib/auth";
import { weekday } from "@/lib/format";
import type { Certificate, TutorDetail, WorkingHour } from "@/lib/types";

const LANGUAGES = CATEGORIES.find((c) => c.id === "languages")!.subjects;
const ALL_SUBJECTS = CATEGORIES.flatMap((c) => c.subjects.map((s) => s.label));

type ProfileForm = {
  headline: string;
  description: string;
  photo_url: string;
  video_url: string;
  country: string;
  native_language: string;
  languages_taught: string[];
  specializations: string[];
  experience_years: number;
  price_cents: number;
  trial_price_cents: number;
  currency: string;
  is_active: boolean;
};

const EMPTY_FORM: ProfileForm = {
  headline: "",
  description: "",
  photo_url: "",
  video_url: "",
  country: "",
  native_language: "",
  languages_taught: [],
  specializations: [],
  experience_years: 0,
  price_cents: 0,
  trial_price_cents: 0,
  currency: "USD",
  is_active: true,
};

type Rule = { weekday: number; enabled: boolean; start_time: string; end_time: string };

function defaultRules(): Rule[] {
  return Array.from({ length: 7 }, (_, weekdayIndex) => ({
    weekday: weekdayIndex,
    enabled: false,
    start_time: "09:00",
    end_time: "18:00",
  }));
}

function rulesFromWorkingHours(hours: WorkingHour[]): Rule[] {
  const rules = defaultRules();
  for (const h of hours) {
    const rule = rules[h.weekday];
    if (!rule) continue;
    rule.enabled = true;
    rule.start_time = h.start_time.slice(0, 5);
    rule.end_time = h.end_time.slice(0, 5);
  }
  return rules;
}

export default function TutorProfilePage() {
  const { user } = useAuth();
  const [form, setForm] = useState<ProfileForm>(EMPTY_FORM);
  const [rules, setRules] = useState<Rule[]>(defaultRules());
  const [busy, setBusy] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<"profile" | "schedule" | null>(null);

  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [certForm, setCertForm] = useState({ title: "", issued_by: "", year: "", file_url: "" });
  const [addingCert, setAddingCert] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const tutor = await get<TutorDetail>("/tutors/me", true);
      setForm({
        headline: tutor.headline ?? "",
        description: tutor.description ?? "",
        photo_url: tutor.photo_url ?? "",
        video_url: tutor.video_url ?? "",
        country: tutor.country ?? "",
        native_language: tutor.native_language ?? "",
        languages_taught: tutor.languages_taught ?? [],
        specializations: tutor.specializations ?? [],
        experience_years: tutor.experience_years ?? 0,
        price_cents: tutor.price_cents ?? 0,
        trial_price_cents: tutor.trial_price_cents ?? 0,
        currency: tutor.currency ?? "USD",
        is_active: tutor.is_active,
      });
      setRules(rulesFromWorkingHours(tutor.working_hours ?? []));
      setCertificates(tutor.certificates ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить профиль");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function addCertificate() {
    if (!certForm.title.trim()) {
      setError("Укажите название сертификата");
      return;
    }
    setAddingCert(true);
    setError(null);
    try {
      const cert = await post<Certificate>(
        "/tutors/me/certificates",
        {
          title: certForm.title,
          issued_by: certForm.issued_by || null,
          year: certForm.year ? Number(certForm.year) : null,
          file_url: certForm.file_url || null,
        },
        true,
      );
      setCertificates((prev) => [...prev, cert]);
      setCertForm({ title: "", issued_by: "", year: "", file_url: "" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось добавить сертификат");
    } finally {
      setAddingCert(false);
    }
  }

  async function removeCertificate(id: string) {
    setCertificates((prev) => prev.filter((c) => c.id !== id));
    await del(`/tutors/me/certificates/${id}`).catch(() => undefined);
  }

  function toggleLanguage(id: string) {
    setForm((f) => ({
      ...f,
      languages_taught: f.languages_taught.includes(id)
        ? f.languages_taught.filter((l) => l !== id)
        : [...f.languages_taught, id],
    }));
  }

  async function saveProfile() {
    setSaving(true);
    setError(null);
    try {
      await post(
        "/tutors/me",
        {
          headline: form.headline || null,
          description: form.description || null,
          photo_url: form.photo_url || null,
          video_url: form.video_url || null,
          country: form.country || null,
          native_language: form.native_language || null,
          languages_taught: form.languages_taught,
          specializations: form.specializations,
          experience_years: form.experience_years,
          price_cents: form.price_cents,
          trial_price_cents: form.trial_price_cents || null,
          currency: form.currency,
          is_active: form.is_active,
        },
        true,
      );
      setSaved("profile");
      setTimeout(() => setSaved(null), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить профиль");
    } finally {
      setSaving(false);
    }
  }

  async function saveSchedule() {
    setSavingSchedule(true);
    setError(null);
    const active = rules.filter((r) => r.enabled);
    try {
      const payload = active.map((r) => ({
        weekday: r.weekday,
        start_time: `${r.start_time}:00`,
        end_time: `${r.end_time}:00`,
      }));
      // Working hours (shown on the public profile) and calendar rules (what
      // actually gates booking — see scheduling/booking) are two separate
      // department tables; both need the same shape saved so browse and
      // booking agree on when this tutor is available.
      await Promise.all([
        put("/tutors/me/working-hours", payload, true),
        put("/calendar/me/rules", payload, true),
      ]);
      setSaved("schedule");
      setTimeout(() => setSaved(null), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить расписание");
    } finally {
      setSavingSchedule(false);
    }
  }

  if (!user || user.role !== "tutor") return null;

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Профиль репетитора</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">
          Расскажите о себе студентам
        </h1>
        <p className="mt-2 text-sm text-ink-3">
          Заполните профиль и расписание, чтобы появиться в каталоге и принимать брони.
        </p>
      </header>

      {busy ? (
        <div className="card mt-8 h-64 animate-pulse bg-line/40" />
      ) : (
        <>
          <section className="card mt-8 space-y-4 p-6">
            <h2 className="display text-lg">Профиль</h2>
            <div>
              <label className="label">Заголовок</label>
              <input
                className="field"
                placeholder="Опытный преподаватель английского"
                value={form.headline}
                onChange={(e) => setForm((f) => ({ ...f, headline: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Описание</label>
              <textarea
                className="field min-h-28 resize-y"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label">Страна (код, напр. GB)</label>
                <input
                  className="field"
                  maxLength={2}
                  value={form.country}
                  onChange={(e) => setForm((f) => ({ ...f, country: e.target.value.toUpperCase() }))}
                />
              </div>
              <div>
                <label className="label">Родной язык</label>
                <select
                  className="field"
                  value={form.native_language}
                  onChange={(e) => setForm((f) => ({ ...f, native_language: e.target.value }))}
                >
                  <option value="">—</option>
                  {LANGUAGES.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="label">Фото (URL)</label>
              <input
                className="field"
                value={form.photo_url}
                onChange={(e) => setForm((f) => ({ ...f, photo_url: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Видео-визитка (URL)</label>
              <input
                className="field"
                value={form.video_url}
                onChange={(e) => setForm((f) => ({ ...f, video_url: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Языки, которым обучаете</label>
              <div className="mt-1 flex flex-wrap gap-2">
                {LANGUAGES.map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    onClick={() => toggleLanguage(l.id)}
                    className={`chip ${form.languages_taught.includes(l.id) ? "!bg-aurora-600 !text-white" : ""}`}
                  >
                    {l.emoji} {l.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Специализации (через запятую)</label>
              <input
                className="field"
                list="specializations-list"
                placeholder={ALL_SUBJECTS.slice(0, 3).join(", ")}
                value={form.specializations.join(", ")}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    specializations: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  }))
                }
              />
              <datalist id="specializations-list">
                {ALL_SUBJECTS.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="label">Опыт (лет)</label>
                <input
                  className="field"
                  type="number"
                  min={0}
                  value={form.experience_years}
                  onChange={(e) => setForm((f) => ({ ...f, experience_years: Number(e.target.value) }))}
                />
              </div>
              <div>
                <label className="label">Цена урока ($)</label>
                <input
                  className="field"
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.price_cents / 100}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, price_cents: Math.round(Number(e.target.value) * 100) }))
                  }
                />
              </div>
              <div>
                <label className="label">Цена пробного ($)</label>
                <input
                  className="field"
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.trial_price_cents / 100}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, trial_price_cents: Math.round(Number(e.target.value) * 100) }))
                  }
                />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              Профиль виден в каталоге
            </label>
            {error && <p className="text-sm text-coral-500">{error}</p>}
            <button className="btn btn-primary !py-2.5 text-sm" disabled={saving} onClick={() => void saveProfile()}>
              {saving ? "Сохраняем…" : saved === "profile" ? "Сохранено ✓" : "Сохранить профиль"}
            </button>
          </section>

          <section className="card mt-6 space-y-4 p-6">
            <h2 className="display text-lg">Сертификаты и дипломы</h2>
            <p className="text-sm text-ink-3">
              Подтверждённое образование повышает доверие студентов при выборе.
            </p>
            {certificates.length > 0 && (
              <ul className="space-y-2">
                {certificates.map((cert) => (
                  <li key={cert.id} className="flex items-start justify-between gap-3 rounded-xl border border-line px-4 py-3">
                    <div>
                      <p className="text-sm font-medium">{cert.title}</p>
                      <p className="text-xs text-ink-3">
                        {[cert.issued_by, cert.year].filter(Boolean).join(" · ") || "—"}
                      </p>
                    </div>
                    <button
                      className="text-xs font-semibold text-coral-500"
                      onClick={() => void removeCertificate(cert.id)}
                    >
                      Удалить
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                className="field"
                placeholder="Название (напр. CELTA)"
                value={certForm.title}
                onChange={(e) => setCertForm((f) => ({ ...f, title: e.target.value }))}
              />
              <input
                className="field"
                placeholder="Кем выдан"
                value={certForm.issued_by}
                onChange={(e) => setCertForm((f) => ({ ...f, issued_by: e.target.value }))}
              />
              <input
                className="field"
                placeholder="Год"
                type="number"
                value={certForm.year}
                onChange={(e) => setCertForm((f) => ({ ...f, year: e.target.value }))}
              />
              <input
                className="field"
                placeholder="Ссылка на скан (необязательно)"
                value={certForm.file_url}
                onChange={(e) => setCertForm((f) => ({ ...f, file_url: e.target.value }))}
              />
            </div>
            <button
              className="btn btn-ghost !py-2 text-sm"
              disabled={addingCert}
              onClick={() => void addCertificate()}
            >
              {addingCert ? "Добавляем…" : "+ Добавить сертификат"}
            </button>
          </section>

          <section className="card mt-6 space-y-4 p-6">
            <h2 className="display text-lg">Расписание</h2>
            <p className="text-sm text-ink-3">
              Отметьте дни и часы, когда вы доступны — студенты смогут бронировать только эти слоты.
            </p>
            <div className="space-y-2">
              {rules.map((r, i) => (
                <div key={r.weekday} className="flex flex-wrap items-center gap-3">
                  <label className="flex w-28 items-center gap-2 text-sm font-medium">
                    <input
                      type="checkbox"
                      checked={r.enabled}
                      onChange={(e) =>
                        setRules((prev) =>
                          prev.map((p, j) => (j === i ? { ...p, enabled: e.target.checked } : p)),
                        )
                      }
                    />
                    {weekday(r.weekday)}
                  </label>
                  <input
                    className="field !w-32"
                    type="time"
                    disabled={!r.enabled}
                    value={r.start_time}
                    onChange={(e) =>
                      setRules((prev) =>
                        prev.map((p, j) => (j === i ? { ...p, start_time: e.target.value } : p)),
                      )
                    }
                  />
                  <span className="text-sm text-ink-3">—</span>
                  <input
                    className="field !w-32"
                    type="time"
                    disabled={!r.enabled}
                    value={r.end_time}
                    onChange={(e) =>
                      setRules((prev) =>
                        prev.map((p, j) => (j === i ? { ...p, end_time: e.target.value } : p)),
                      )
                    }
                  />
                </div>
              ))}
            </div>
            <button
              className="btn btn-primary !py-2.5 text-sm"
              disabled={savingSchedule}
              onClick={() => void saveSchedule()}
            >
              {savingSchedule ? "Сохраняем…" : saved === "schedule" ? "Сохранено ✓" : "Сохранить расписание"}
            </button>
          </section>
        </>
      )}
    </div>
  );
}
