"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { get, put } from "@/lib/api";
import { Paginated } from "@/components/paginated";
import { money } from "@/lib/format";
import type { AdminAction, AdminDashboard, AnalyticsSummary, SystemSetting } from "@/lib/types";

function todayRange() {
  const to = new Date().toISOString().slice(0, 10);
  const from = new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString().slice(0, 10);
  return { from, to };
}

type TopEvent = { event_type: string; count: number };

export default function AdminPage() {
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [actions, setActions] = useState<AdminAction[]>([]);
  const [topEvents, setTopEvents] = useState<TopEvent[]>([]);

  const [editingSetting, setEditingSetting] = useState<string | null>(null);
  const [settingDraft, setSettingDraft] = useState("");
  const [settingError, setSettingError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { from, to } = todayRange();
    const [dash, an, sett, act, top] = await Promise.all([
      get<AdminDashboard>("/admin/dashboard", true).catch(() => null),
      get<AnalyticsSummary>(`/analytics/metrics/summary?date_from=${from}&date_to=${to}`, true).catch(() => null),
      get<SystemSetting[]>("/admin/settings", true).catch(() => [] as SystemSetting[]),
      get<AdminAction[]>("/admin/actions", true).catch(() => [] as AdminAction[]),
      get<TopEvent[]>("/analytics/metrics/top-events?limit=8", true).catch(() => [] as TopEvent[]),
    ]);
    setDashboard(dash);
    setAnalytics(an);
    setSettings(sett);
    setActions(act);
    setTopEvents(top);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

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

  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Админ</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Панель управления</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/admin/lessons" className="btn btn-ghost">
            Аналитика уроков →
          </Link>
          <Link href="/dashboard/admin/users" className="btn btn-primary">
            Управление пользователями →
          </Link>
        </div>
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
