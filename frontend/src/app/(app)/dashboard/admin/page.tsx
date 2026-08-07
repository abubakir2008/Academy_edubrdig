"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { del, get, post, put } from "@/lib/api";
import { Paginated } from "@/components/paginated";
import { money } from "@/lib/format";
import type {
  AdminAction,
  AdminDashboard,
  AnalyticsSummary,
  Category,
  StudentLead,
  SystemSetting,
} from "@/lib/types";

const EMPTY_CATEGORY = { slug: "", name: "", group: "" };

function todayRange() {
  const to = new Date().toISOString().slice(0, 10);
  const from = new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString().slice(0, 10);
  return { from, to };
}

type TopEvent = { event_type: string; count: number };

export default function AdminPage() {
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [actions, setActions] = useState<AdminAction[]>([]);
  const [leads, setLeads] = useState<StudentLead[]>([]);
  const [topEvents, setTopEvents] = useState<TopEvent[]>([]);

  const [catForm, setCatForm] = useState(EMPTY_CATEGORY);
  const [editingCat, setEditingCat] = useState<string | null>(null);

  const [editingSetting, setEditingSetting] = useState<string | null>(null);
  const [settingDraft, setSettingDraft] = useState("");
  const [settingError, setSettingError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { from, to } = todayRange();
    const [dash, an, cats, sett, act, ld, top] = await Promise.all([
      get<AdminDashboard>("/admin/dashboard", true).catch(() => null),
      get<AnalyticsSummary>(`/analytics/metrics/summary?date_from=${from}&date_to=${to}`, true).catch(() => null),
      get<Category[]>("/admin/categories", true).catch(() => [] as Category[]),
      get<SystemSetting[]>("/admin/settings", true).catch(() => [] as SystemSetting[]),
      get<AdminAction[]>("/admin/actions", true).catch(() => [] as AdminAction[]),
      get<StudentLead[]>("/students/leads", true).catch(() => [] as StudentLead[]),
      get<TopEvent[]>("/analytics/metrics/top-events?limit=8", true).catch(() => [] as TopEvent[]),
    ]);
    setDashboard(dash);
    setAnalytics(an);
    setCategories(cats);
    setSettings(sett);
    setActions(act);
    setLeads(ld);
    setTopEvents(top);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveCategory() {
    if (!catForm.slug || !catForm.name) return;
    const payload = { slug: catForm.slug, name: catForm.name, group: catForm.group || null };
    if (editingCat) {
      await put(`/admin/categories/${editingCat}`, payload, true).catch(() => undefined);
    } else {
      await post("/admin/categories", payload, true).catch(() => undefined);
    }
    setCatForm(EMPTY_CATEGORY);
    setEditingCat(null);
    await load();
  }

  async function removeCategory(id: string) {
    await del(`/admin/categories/${id}`).catch(() => undefined);
    await load();
  }

  function startEditSetting(s: SystemSetting) {
    setEditingSetting(s.key);
    setSettingDraft(JSON.stringify(s.value, null, 2));
    setSettingError(null);
  }

  async function saveSetting(category: string) {
    if (!editingSetting) return;
    setSettingError(null);
    let value: Record<string, unknown>;
    try {
      value = JSON.parse(settingDraft);
    } catch {
      setSettingError("Значение должно быть корректным JSON");
      return;
    }
    try {
      await put(`/admin/settings/${editingSetting}`, { category, value }, true);
      setEditingSetting(null);
      await load();
    } catch (e) {
      setSettingError(e instanceof Error ? e.message : "Не удалось сохранить");
    }
  }

  // Categories per group — feeds the chart at the bottom of the page.
  const categoriesByGroup = Object.entries(
    categories.reduce<Record<string, number>>((acc, c) => {
      const key = c.group || "без группы";
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {}),
  )
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Админ</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Панель управления</h1>
        </div>
        <Link href="/dashboard/admin/users" className="btn btn-primary">
          Управление пользователями →
        </Link>
      </header>

      <section className="mt-8 grid gap-4 sm:grid-cols-3">
        <div className="card p-5">
          <p className="text-xs text-ink-3">Событий за 30 дней</p>
          <p className="display mt-1 text-2xl">{analytics?.total_events ?? "—"}</p>
        </div>
        <div className="card p-5">
          <p className="text-xs text-ink-3">Уникальных пользователей</p>
          <p className="display mt-1 text-2xl">{analytics?.unique_users ?? "—"}</p>
        </div>
        <div className="card p-5">
          <p className="text-xs text-ink-3">Выручка (события)</p>
          <p className="display mt-1 text-2xl">{analytics ? money(analytics.revenue_cents) : "—"}</p>
        </div>
      </section>
      {dashboard && <p className="mt-3 text-xs text-ink-3">{dashboard.note}</p>}

      <section className="mt-10">
        <h2 className="display text-lg">Категории</h2>
        <div className="card mt-4 p-6">
          <div className="grid gap-3 sm:grid-cols-3">
            <input
              className="field"
              placeholder="slug"
              value={catForm.slug}
              disabled={!!editingCat}
              onChange={(e) => setCatForm((f) => ({ ...f, slug: e.target.value }))}
            />
            <input
              className="field"
              placeholder="Название"
              value={catForm.name}
              onChange={(e) => setCatForm((f) => ({ ...f, name: e.target.value }))}
            />
            <input
              className="field"
              placeholder="Группа (необязательно)"
              value={catForm.group}
              onChange={(e) => setCatForm((f) => ({ ...f, group: e.target.value }))}
            />
          </div>
          <div className="mt-3 flex gap-2">
            <button className="btn btn-primary !py-2 text-sm" onClick={() => void saveCategory()}>
              {editingCat ? "Сохранить" : "Создать"}
            </button>
            {editingCat && (
              <button
                className="btn btn-ghost !py-2 text-sm"
                onClick={() => {
                  setEditingCat(null);
                  setCatForm(EMPTY_CATEGORY);
                }}
              >
                Отмена
              </button>
            )}
          </div>
        </div>

        <Paginated
          items={categories}
          empty="Категорий пока нет."
          renderItem={(c) => (
            <li key={c.id} className="card flex h-full flex-col justify-between gap-3 p-4">
              <span className="text-sm">
                <b className="font-semibold">{c.name}</b>{" "}
                <span className="text-ink-3">
                  /{c.slug}
                  {c.group ? ` · ${c.group}` : ""}
                </span>
              </span>
              <div className="flex gap-2">
                <button
                  className="btn btn-ghost !py-1.5 text-xs"
                  onClick={() => {
                    setEditingCat(c.id);
                    setCatForm({ slug: c.slug, name: c.name, group: c.group ?? "" });
                  }}
                >
                  Изменить
                </button>
                <button className="btn btn-ghost !py-1.5 text-xs text-coral-500" onClick={() => void removeCategory(c.id)}>
                  Удалить
                </button>
              </div>
            </li>
          )}
        />
      </section>

      <section className="mt-10">
        <h2 className="display text-lg">Заявки с онбординга</h2>
        <Paginated
          items={leads}
          empty="Заявок пока нет."
          renderItem={(lead) => (
            <li key={lead.id} className="card h-full p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <b className="font-semibold">{lead.full_name}</b>
                <span className="text-xs text-ink-3">{new Date(lead.created_at).toLocaleString("ru-RU")}</span>
              </div>
              <p className="mt-1 text-ink-3">
                {[lead.contact_phone, lead.contact_email].filter(Boolean).join(" · ") || "Без контакта"}
              </p>
              <dl className="mt-2 space-y-0.5 text-xs text-ink-3">
                {lead.subject && (
                  <div>
                    <dt className="inline font-semibold text-ink-2">Учит: </dt>
                    <dd className="inline">{lead.subject}</dd>
                  </div>
                )}
                {lead.goal && (
                  <div>
                    <dt className="inline font-semibold text-ink-2">Зачем: </dt>
                    <dd className="inline">{lead.goal}</dd>
                  </div>
                )}
                {lead.date_of_birth && (
                  <div>
                    <dt className="inline font-semibold text-ink-2">Д.р.: </dt>
                    <dd className="inline">{lead.date_of_birth}</dd>
                  </div>
                )}
                {lead.study_place && (
                  <div>
                    <dt className="inline font-semibold text-ink-2">Где учится: </dt>
                    <dd className="inline">{lead.study_place}</dd>
                  </div>
                )}
                {lead.destination_country && (
                  <div>
                    <dt className="inline font-semibold text-ink-2">Переезд: </dt>
                    <dd className="inline">{lead.destination_country}</dd>
                  </div>
                )}
              </dl>
            </li>
          )}
        />
      </section>

      <section className="mt-10">
        <h2 className="display text-lg">Настройки платформы</h2>
        <Paginated
          items={settings}
          empty="Настроек пока нет."
          renderItem={(s) => (
            <li key={s.key} className="card h-full p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span>
                  <b className="font-semibold">{s.key}</b> <span className="text-ink-3">({s.category})</span>
                </span>
                {editingSetting !== s.key && (
                  <button className="text-xs font-semibold text-aurora-700" onClick={() => startEditSetting(s)}>
                    Изменить
                  </button>
                )}
              </div>
              {editingSetting === s.key ? (
                <div className="mt-2 space-y-2">
                  <textarea
                    className="field min-h-24 resize-y font-mono text-xs"
                    value={settingDraft}
                    onChange={(e) => setSettingDraft(e.target.value)}
                  />
                  {settingError && <p className="text-xs text-coral-500">{settingError}</p>}
                  <div className="flex gap-2">
                    <button className="btn btn-primary !py-1.5 text-xs" onClick={() => void saveSetting(s.category)}>
                      Сохранить
                    </button>
                    <button className="btn btn-ghost !py-1.5 text-xs" onClick={() => setEditingSetting(null)}>
                      Отмена
                    </button>
                  </div>
                </div>
              ) : (
                <pre className="mt-1 overflow-x-auto text-xs text-ink-3">{JSON.stringify(s.value)}</pre>
              )}
            </li>
          )}
        />
      </section>

      <section className="mt-10">
        <h2 className="display text-lg">Журнал действий</h2>
        <Paginated
          items={actions}
          empty="Действий пока не зафиксировано."
          renderItem={(a) => (
            <li key={a.id} className="card h-full p-4 text-sm">
              <b className="font-semibold">{a.action}</b>
              {a.target_type && (
                <span className="text-ink-3">
                  {" "}
                  · {a.target_type} {a.target_id}
                </span>
              )}
              <p className="mt-1 text-xs text-ink-3">{new Date(a.created_at).toLocaleString("ru-RU")}</p>
            </li>
          )}
        />
      </section>

      <section className="mt-10">
        <h2 className="display text-lg">Графики</h2>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <BarChart title="Категории по группам" data={categoriesByGroup} />
          <BarChart
            title="Топ событий за всё время"
            data={topEvents.map((e) => ({ label: e.event_type, value: e.count }))}
          />
        </div>
      </section>
    </div>
  );
}

/* ------------------------------ Pieces --------------------------------- */

function BarChart({ title, data }: { title: string; data: { label: string; value: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="card p-6">
      <h3 className="display text-base">{title}</h3>
      {data.length ? (
        <div className="mt-5 space-y-3">
          {data.map((d) => (
            <div key={d.label}>
              <div className="flex items-center justify-between gap-2 text-xs text-ink-3">
                <span className="truncate">{d.label}</span>
                <span className="shrink-0 font-semibold text-ink-2">{d.value}</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-line" title={`${d.label}: ${d.value}`}>
                <div className="h-full rounded-full bg-aurora-600" style={{ width: `${(d.value / max) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-ink-3">Данных пока нет.</p>
      )}
    </div>
  );
}
