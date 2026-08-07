"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { get, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/format";
import type { Booking, LessonPackage, TutorDetail } from "@/lib/types";

const DURATIONS = [30, 50, 60, 90];

/**
 * Slot picker. The tutor publishes weekly `working_hours`, so we offer the next
 * 14 days that fall on a working weekday and generate hourly starts inside the
 * published window. The final overlap check is the backend's (409 on conflict).
 */
export function BookingPanel({ tutor }: { tutor: TutorDetail }) {
  const { user, loading } = useAuth();
  const [isTrial, setIsTrial] = useState(tutor.trial_price_cents != null);
  const [duration, setDuration] = useState(50);
  const [day, setDay] = useState<string>("");
  const [time, setTime] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booked, setBooked] = useState<Booking | null>(null);
  const [usablePackage, setUsablePackage] = useState<LessonPackage | null>(null);
  const [usePackage, setUsePackage] = useState(true);

  useEffect(() => {
    if (!user || user.role !== "student") return;
    get<LessonPackage[]>("/payments/packages/me", true)
      .then((packages) => setUsablePackage(packages.find((p) => p.tutor_id === tutor.user_id) ?? null))
      .catch(() => undefined);
  }, [user, tutor.user_id]);

  const days = useMemo(() => availableDays(tutor), [tutor]);
  const times = useMemo(() => (day ? slotsForDay(tutor, day, duration) : []), [tutor, day, duration]);

  const price = isTrial && tutor.trial_price_cents != null ? tutor.trial_price_cents : tutor.price_cents;
  const payingWithPackage = usablePackage && usePackage && !isTrial;

  async function submit() {
    if (!day || !time) {
      setError("Выберите дату и время");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // `time` is already a full UTC instant (see slotsForDay) — the tutor's
      // published hours are UTC wall-clock, so there is no local time to
      // reconstruct here; doing so previously shifted every booking by the
      // browser's UTC offset and made valid slots look unavailable.
      const booking = await post<Booking>(
        "/booking",
        {
          tutor_id: tutor.user_id,
          scheduled_start: time,
          duration_minutes: duration,
          is_trial: isTrial,
          package_id: payingWithPackage ? usablePackage.id : undefined,
        },
        true,
      );
      setBooked(booking);
    } catch (e) {
      setError(translateBookingError(e));
    } finally {
      setBusy(false);
    }
  }

  if (booked) {
    return (
      <div className="mt-6 rounded-2xl bg-jade-100 p-4 text-sm text-jade-700">
        <p className="font-semibold">Урок забронирован</p>
        <p className="mt-1">
          {new Date(booked.scheduled_start).toLocaleString("ru-RU", {
            dateStyle: "long",
            timeStyle: "short",
          })}{" "}
          · {booked.package_id ? "оплачено пакетом" : money(booked.price_cents, booked.currency)}
        </p>
        <Link href="/dashboard/bookings" className="btn btn-primary mt-4 w-full !py-2.5 text-sm">
          {booked.package_id ? "Перейти к бронированиям" : "Перейти к оплате в кабинете"}
        </Link>
      </div>
    );
  }

  if (!loading && !user) {
    return (
      <div className="mt-6 space-y-3">
        <Link href={`/login?next=/tutors/${tutor.user_id}`} className="btn btn-primary w-full">
          Войти и записаться
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-4">
      {tutor.trial_price_cents != null && (
        <div className="flex rounded-xl bg-paper p-1 text-sm">
          {[
            { value: true, label: "Пробный" },
            { value: false, label: "Обычный урок" },
          ].map((option) => (
            <button
              key={String(option.value)}
              onClick={() => setIsTrial(option.value)}
              className={`flex-1 rounded-lg px-3 py-2 font-medium transition-colors ${
                isTrial === option.value ? "bg-paper-2 shadow-sm" : "text-ink-3"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}

      {usablePackage && !isTrial && (
        <label className="flex items-center gap-2.5 rounded-xl bg-jade-100 px-3.5 py-2.5 text-sm text-jade-700">
          <input type="checkbox" checked={usePackage} onChange={(e) => setUsePackage(e.target.checked)} />
          Списать урок из пакета ({usablePackage.lessons_remaining} осталось)
        </label>
      )}

      <div>
        <label className="label" htmlFor="day">
          Дата
        </label>
        <select
          id="day"
          className="field"
          value={day}
          onChange={(e) => {
            setDay(e.target.value);
            setTime("");
          }}
        >
          <option value="">Выберите день</option>
          {days.map((d) => (
            <option key={d.value} value={d.value}>
              {d.label}
            </option>
          ))}
        </select>
        {days.length === 0 && (
          <p className="mt-2 text-xs text-ink-3">
            Репетитор ещё не опубликовал расписание — напишите ему в чате после регистрации.
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label" htmlFor="time">
            Время
          </label>
          <select
            id="time"
            className="field"
            value={time}
            disabled={!day}
            onChange={(e) => setTime(e.target.value)}
          >
            <option value="">—</option>
            {times.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="duration">
            Длительность
          </label>
          <select
            id="duration"
            className="field"
            value={duration}
            onChange={(e) => {
              setDuration(Number(e.target.value));
              setTime("");
            }}
          >
            {DURATIONS.map((d) => (
              <option key={d} value={d}>
                {d} мин
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="text-sm text-coral-500">{error}</p>}

      <button className="btn btn-primary w-full" onClick={() => void submit()} disabled={busy}>
        {busy
          ? "Бронируем…"
          : payingWithPackage
            ? "Забронировать · из пакета"
            : `Забронировать · ${money(price, tutor.currency)}`}
      </button>
    </div>
  );
}

/* ------------------------------ Slot math -------------------------------
 * The tutor's `working_hours` are wall-clock UTC (the backend's calendar
 * enforcement normalises every request to UTC before comparing — see
 * scheduling/calendar/crud/calendar.py::is_available), not the browser's
 * local timezone. Everything below therefore works in UTC calendar days and
 * only converts to the visitor's local time for display, at the last
 * possible step — the value submitted is always the exact UTC instant a
 * slot represents. */

function availableDays(tutor: TutorDetail) {
  const weekdays = new Set(tutor.working_hours.map((h) => h.weekday));
  const days: { value: string; label: string }[] = [];
  const now = new Date();

  for (let offset = 1; offset <= 14 && days.length < 10; offset += 1) {
    const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + offset));
    // `working_hours.weekday` is 0=Monday, JS getUTCDay() is 0=Sunday.
    const weekday = (date.getUTCDay() + 6) % 7;
    if (!weekdays.has(weekday)) continue;
    days.push({
      value: toDateInput(date),
      // Rendered from a UTC-midnight instant, so the calendar day shown
      // matches the UTC day this option represents in every timezone.
      label: date.toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" }),
    });
  }
  return days;
}

/** Returns slots as {value: ISO instant, label: time in the visitor's local zone}. */
function slotsForDay(tutor: TutorDetail, day: string, duration: number): { value: string; label: string }[] {
  const [y, m, d] = day.split("-").map(Number);
  const weekday = (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7;
  const slots = new Map<string, string>();

  for (const window of tutor.working_hours.filter((h) => h.weekday === weekday)) {
    const start = toMinutes(window.start_time);
    const end = toMinutes(window.end_time);
    for (let mins = start; mins + duration <= end; mins += 30) {
      const instant = new Date(Date.UTC(y, m - 1, d, Math.floor(mins / 60), mins % 60));
      slots.set(instant.toISOString(), instant.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }));
    }
  }
  return [...slots.entries()].sort().map(([value, label]) => ({ value, label }));
}

const pad = (n: number) => String(n).padStart(2, "0");
const toMinutes = (time: string) => {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
};
const toDateInput = (date: Date) =>
  `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;

const BOOKING_ERRORS: Record<string, string> = {
  "The tutor already has a booking in this time slot": "У репетитора уже есть урок на это время — выберите другой слот",
  "The tutor is not available at the requested time": "Репетитор не ведёт приём в это время — выберите другой день или час",
  "You've already used your trial lesson with this tutor": "Пробный урок с этим репетитором уже был использован",
  "Tutor has no price set for this lesson type": "У репетитора не указана цена за этот тип урока",
};

function translateBookingError(e: unknown): string {
  const message = e instanceof Error ? e.message : "";
  return BOOKING_ERRORS[message] ?? message ?? "Не удалось забронировать урок";
}
