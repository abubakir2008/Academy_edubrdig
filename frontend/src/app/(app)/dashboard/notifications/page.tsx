"use client";

import { useCallback, useEffect, useState } from "react";

import { get, post } from "@/lib/api";
import type { AppNotification } from "@/lib/types";

export default function NotificationsPage() {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [busy, setBusy] = useState(true);

  const load = useCallback(async () => {
    setBusy(true);
    const list = await get<AppNotification[]>("/notifications/me", true).catch(() => [] as AppNotification[]);
    setItems(list);
    setBusy(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function markRead(id: string) {
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    await post(`/notifications/${id}/read`, undefined, true).catch(() => undefined);
  }

  async function markAllRead() {
    setItems((prev) => prev.map((n) => ({ ...n, read: true })));
    await post("/notifications/read-all", undefined, true).catch(() => undefined);
  }

  const unread = items.filter((n) => !n.read).length;

  return (
    <div className="mx-auto max-w-3xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Уведомления</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Входящие</h1>
        </div>
        {unread > 0 && (
          <button className="btn btn-ghost !py-2 text-sm" onClick={() => void markAllRead()}>
            Прочитать все ({unread})
          </button>
        )}
      </header>

      <div className="mt-8">
        {busy ? (
          <div className="card h-24 animate-pulse bg-line/40" />
        ) : items.length ? (
          <ul className="space-y-2">
            {items.map((n) => (
              <li
                key={n.id}
                className={`card flex items-start justify-between gap-4 p-4 ${n.read ? "opacity-70" : ""}`}
              >
                <div>
                  <p className="text-sm font-medium">
                    {!n.read && <span className="mr-2 inline-block h-2 w-2 rounded-full bg-aurora-600" />}
                    {n.title}
                  </p>
                  {n.body && <p className="mt-1 text-sm text-ink-3">{n.body}</p>}
                  <p className="mt-1 text-xs text-ink-3">
                    {new Date(n.created_at).toLocaleString("ru-RU")}
                  </p>
                </div>
                {!n.read && (
                  <button className="text-xs font-semibold text-aurora-700" onClick={() => void markRead(n.id)}>
                    Прочитано
                  </button>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="card p-6 text-sm text-ink-3">Уведомлений пока нет.</p>
        )}
      </div>
    </div>
  );
}
