"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { badgesFor } from "@/lib/badges";
import { get } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/format";
import type { Booking, TutorDetail, Wallet } from "@/lib/types";

import { BookingRow } from "./booking-row";

/** Overview tab: a snapshot, not the full list — bookings/payments/wallet
 * each got their own tab once there was enough here to need one. */
export function DashboardOverview() {
  const { user } = useAuth();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [tutorProfile, setTutorProfile] = useState<TutorDetail | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [busy, setBusy] = useState(true);

  const load = useCallback(async () => {
    if (!user) return;
    setBusy(true);
    const role = user.role === "tutor" ? "tutor" : "student";
    const [myBookings, profile, myWallet] = await Promise.all([
      get<Booking[]>(`/booking/me?role=${role}`, true).catch(() => [] as Booking[]),
      user.role === "tutor" ? get<TutorDetail>(`/tutors/${user.id}`).catch(() => null) : Promise.resolve(null),
      user.role === "tutor" ? get<Wallet>("/wallet/me", true).catch(() => null) : Promise.resolve(null),
    ]);
    setBookings(myBookings);
    setTutorProfile(profile);
    setWallet(myWallet);
    setBusy(false);
  }, [user]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!user) return null;

  const isStaff = user.role !== "student" && user.role !== "tutor";
  const upcoming = bookings
    .filter((b) => new Date(b.scheduled_start) >= new Date() && b.status !== "cancelled")
    .sort((a, b) => a.scheduled_start.localeCompare(b.scheduled_start));
  const next = upcoming[0];

  return (
    <div className="mx-auto max-w-5xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">
          Обзор
        </p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">
          Привет, {user.full_name || user.email}
        </h1>
      </header>

      {isStaff ? (
        <div className="card mt-8 p-6 text-sm">
          <b className="font-semibold">Роль: {user.role}.</b> Ваши инструменты — во вкладках снизу
          (Админ, Модерация, Тикеты и т.д., в зависимости от роли), не здесь на общем обзоре.
        </div>
      ) : (
        <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="space-y-6">
            <section>
              <div className="flex items-center justify-between">
                <h2 className="display text-lg">Ближайший урок</h2>
                <Link href="/dashboard/bookings" className="text-sm font-semibold text-aurora-700">
                  Все брони →
                </Link>
              </div>
              {busy ? (
                <div className="card mt-4 h-24 animate-pulse bg-line/40" />
              ) : next ? (
                <div className="mt-4">
                  <BookingRow booking={next} asRole={user.role === "tutor" ? "tutor" : "student"} />
                </div>
              ) : (
                <p className="card mt-4 p-6 text-sm text-ink-3">
                  Запланированных уроков нет.{" "}
                  {user.role === "student" && (
                    <Link href="/tutors" className="font-semibold text-aurora-700">
                      Выбрать репетитора →
                    </Link>
                  )}
                </p>
              )}
            </section>

            {user.role === "tutor" && !busy && !tutorProfile?.headline && (
              <section className="card p-6">
                <h2 className="display text-lg">Настройте профиль</h2>
                <p className="mt-2 text-sm text-ink-3">
                  Без заполненного профиля и расписания вы не появитесь в каталоге и не сможете
                  принимать брони.
                </p>
                <Link href="/dashboard/profile" className="btn btn-primary mt-4 w-full !py-2.5 text-sm">
                  Заполнить профиль →
                </Link>
              </section>
            )}

            {user.role === "tutor" && tutorProfile?.headline && (
              <section className="card p-6">
                <h2 className="display text-lg">Профиль</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  {badgesFor(tutorProfile).map((b) => (
                    <span key={b.id} className={`chip ${b.tone}`}>
                      {b.emoji} {b.label}
                    </span>
                  ))}
                  {badgesFor(tutorProfile).length === 0 && (
                    <span className="text-sm text-ink-3">
                      Пока без значков — они появятся по мере отзывов и уроков.
                    </span>
                  )}
                </div>
                {!tutorProfile.is_verified && (
                  <Link
                    href="/dashboard/verification"
                    className="btn btn-primary mt-4 w-full !py-2.5 text-sm"
                  >
                    Пройти верификацию →
                  </Link>
                )}
              </section>
            )}
          </div>

          <aside className="space-y-6">
            {user.role === "tutor" && (
              <div className="card p-6">
                <h2 className="display text-lg">Баланс</h2>
                <p className="display mt-2 text-3xl">
                  {wallet ? money(wallet.balance_cents, wallet.currency) : "—"}
                </p>
                <Link href="/dashboard/wallet" className="btn btn-ghost mt-4 w-full !py-2 text-sm">
                  Кошелёк →
                </Link>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
