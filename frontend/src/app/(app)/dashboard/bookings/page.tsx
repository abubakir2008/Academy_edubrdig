"use client";

import { useCallback, useEffect, useState } from "react";

import { get } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Booking } from "@/lib/types";

import { BookingRow } from "../booking-row";

const TABS = [
  { id: "upcoming", label: "Ближайшие" },
  { id: "past", label: "История" },
] as const;

export default function BookingsPage() {
  const { user } = useAuth();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [busy, setBusy] = useState(true);
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("upcoming");

  const asRole = user?.role === "tutor" ? "tutor" : "student";

  const load = useCallback(async () => {
    if (!user) return;
    setBusy(true);
    const items = await get<Booking[]>(`/booking/me?role=${asRole}`, true).catch(() => [] as Booking[]);
    setBookings(items);
    setBusy(false);
  }, [user, asRole]);

  useEffect(() => {
    void load();
  }, [load]);

  const upcoming = bookings
    .filter((b) => new Date(b.scheduled_start) >= new Date() && b.status !== "cancelled")
    .sort((a, b) => a.scheduled_start.localeCompare(b.scheduled_start));
  const past = bookings
    .filter((b) => !upcoming.includes(b))
    .sort((a, b) => b.scheduled_start.localeCompare(a.scheduled_start));
  const shown = tab === "upcoming" ? upcoming : past;

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">
          Бронирования
        </p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Ваши уроки</h1>
      </header>

      <div className="mt-6 flex rounded-xl bg-paper-2 p-1 text-sm">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 rounded-lg px-3 py-2 font-medium transition-colors ${
              tab === t.id ? "bg-ink text-paper-2" : "text-ink-3 hover:text-ink"
            }`}
          >
            {t.label} {t.id === "upcoming" && upcoming.length > 0 ? `(${upcoming.length})` : ""}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {busy ? (
          <div className="card h-24 animate-pulse bg-line/40" />
        ) : shown.length ? (
          <ul className="space-y-3">
            {shown.map((b) => (
              <BookingRow key={b.id} booking={b} asRole={asRole} muted={tab === "past"} onChanged={load} />
            ))}
          </ul>
        ) : (
          <p className="card p-6 text-sm text-ink-3">
            {tab === "upcoming" ? "Запланированных уроков нет." : "История пуста."}
          </p>
        )}
      </div>
    </div>
  );
}
