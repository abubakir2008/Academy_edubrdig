"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { get, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/format";
import type { Booking, LessonPackage, Payment, Student, TutorSummary } from "@/lib/types";

const PACKAGE_TIERS = [
  { count: 5, discount: "−8%" },
  { count: 10, discount: "−15%" },
  { count: 20, discount: "−20%" },
];

export function PaymentsView() {
  const { user } = useAuth();
  const params = useSearchParams();
  const disputePaymentId = params.get("dispute");

  const [bookings, setBookings] = useState<Booking[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [packages, setPackages] = useState<LessonPackage[]>([]);
  const [favorites, setFavorites] = useState<TutorSummary[]>([]);
  const [busy, setBusy] = useState(true);
  const [payingId, setPayingId] = useState<string | null>(null);
  const [buyingFor, setBuyingFor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isStudent = user?.role !== "tutor";

  const load = useCallback(async () => {
    if (!user) return;
    setBusy(true);
    const role = isStudent ? "student" : "tutor";
    const [b, p, pkgs, me] = await Promise.all([
      get<Booking[]>(`/booking/me?role=${role}`, true).catch(() => [] as Booking[]),
      get<Payment[]>(`/payments/me?role=${role}`, true).catch(() => [] as Payment[]),
      isStudent ? get<LessonPackage[]>("/payments/packages/me", true).catch(() => [] as LessonPackage[]) : Promise.resolve([]),
      isStudent ? get<Student>("/students/me", true).catch(() => null) : Promise.resolve(null),
    ]);
    setBookings(b);
    setPayments(p);
    setPackages(pkgs);
    if (me) {
      const resolved = await Promise.all(
        me.favorites.map((f) => get<TutorSummary>(`/tutors/${f.tutor_id}`).catch(() => null)),
      );
      setFavorites(resolved.filter((t): t is TutorSummary => t !== null));
    }
    setBusy(false);
  }, [user, isStudent]);

  useEffect(() => {
    void load();
  }, [load]);

  const unpaid = bookings.filter(
    (b) => b.status !== "cancelled" && !b.payment_id && !b.package_id,
  );

  async function payBooking(bookingId: string) {
    setPayingId(bookingId);
    setError(null);
    try {
      await post("/payments/checkout", { booking_id: bookingId }, true);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Оплата не прошла");
    } finally {
      setPayingId(null);
    }
  }

  async function buyPackage(tutorId: string, count: number) {
    setBuyingFor(tutorId + count);
    setError(null);
    try {
      await post("/payments/packages/checkout", { tutor_id: tutorId, lesson_count: count }, true);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось купить пакет");
    } finally {
      setBuyingFor(null);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Оплата</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Платежи и пакеты</h1>
      </header>

      {error && <p className="card mt-4 border-coral-500/40 bg-coral-100 p-4 text-sm">{error}</p>}

      {disputePaymentId && <DisputeForm paymentId={disputePaymentId} />}

      {isStudent && (
        <section className="mt-8">
          <h2 className="display text-lg">Ждут оплаты</h2>
          {busy ? (
            <div className="card mt-4 h-16 animate-pulse bg-line/40" />
          ) : unpaid.length ? (
            <ul className="mt-4 space-y-3">
              {unpaid.map((b) => (
                <li key={b.id} className="card flex flex-wrap items-center justify-between gap-3 p-5">
                  <div>
                    <p className="font-semibold">
                      {new Date(b.scheduled_start).toLocaleString("ru-RU", { dateStyle: "long", timeStyle: "short" })}
                    </p>
                    <p className="mt-1 text-sm text-ink-3">
                      {b.is_trial ? "Пробный урок" : "Урок"} · {money(b.price_cents, b.currency)}
                    </p>
                  </div>
                  <button
                    className="btn btn-primary !py-2 text-sm"
                    disabled={payingId === b.id}
                    onClick={() => void payBooking(b.id)}
                  >
                    {payingId === b.id ? "Оплачиваем…" : `Оплатить · ${money(b.price_cents, b.currency)}`}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="card mt-4 p-6 text-sm text-ink-3">Всё оплачено — ничего не ждёт.</p>
          )}
        </section>
      )}

      {isStudent && packages.length > 0 && (
        <section className="mt-8">
          <h2 className="display text-lg">Ваши пакеты</h2>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {packages.map((p) => (
              <li key={p.id} className="card p-5">
                <p className="font-semibold">
                  {p.lessons_remaining} из {p.total_lessons} уроков осталось
                </p>
                <p className="mt-1 text-sm text-ink-3">{money(p.price_cents, p.currency)} за пакет</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {isStudent && favorites.length > 0 && (
        <section className="mt-8">
          <h2 className="display text-lg">Купить пакет уроков</h2>
          <p className="mt-1 text-sm text-ink-3">
            Оплатите несколько уроков сразу со скидкой — репетитор получает деньги сразу,
            уроки списываются по одному при бронировании.
          </p>
          <ul className="mt-4 space-y-4">
            {favorites.map((t) => (
              <li key={t.user_id} className="card p-5">
                <p className="font-semibold">{t.headline || "Репетитор"}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {PACKAGE_TIERS.map((tier) => (
                    <button
                      key={tier.count}
                      className="btn btn-ghost !py-2 text-sm"
                      disabled={buyingFor === t.user_id + tier.count}
                      onClick={() => void buyPackage(t.user_id, tier.count)}
                    >
                      {buyingFor === t.user_id + tier.count
                        ? "…"
                        : `${tier.count} уроков ${tier.discount}`}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-8">
        <h2 className="display text-lg">История платежей</h2>
        {busy ? (
          <div className="card mt-4 h-16 animate-pulse bg-line/40" />
        ) : payments.length ? (
          <ul className="mt-4 space-y-3">
            {payments.map((p) => (
              <li key={p.id} className="card flex flex-wrap items-center justify-between gap-3 p-5">
                <div>
                  <p className="font-semibold">
                    {money(p.amount_cents, p.currency)}
                    {p.gateway === "mock" && (
                      <span className="chip ml-2 !bg-citrus-100 !text-citrus-700 text-xs" title="Оплата не проходила через реальный платёжный шлюз — тестовый режим сервиса">
                        тестовый платёж
                      </span>
                    )}
                  </p>
                  <p className="mt-1 text-sm text-ink-3">
                    {new Date(p.created_at).toLocaleDateString("ru-RU")} · {p.status} · {p.quantity} урок(ов)
                    {p.refunds.length > 0 && ` · возврат ${money(p.refunds[0].amount_cents, p.currency)}`}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="card mt-4 p-6 text-sm text-ink-3">Платежей ещё не было.</p>
        )}
      </section>
    </div>
  );
}

function DisputeForm({ paymentId }: { paymentId: string }) {
  const [reason, setReason] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await post(
        "/support/tickets",
        {
          subject: "Спор по платежу",
          message: reason || "Прошу разобраться с платежом.",
          kind: "dispute",
          payment_id: paymentId,
        },
        true,
      );
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось открыть спор");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <div className="card mt-6 border-jade-500/40 bg-jade-100 p-5 text-sm text-jade-700">
        Спор открыт — служба поддержки свяжется с вами в разделе «Сообщения».
      </div>
    );
  }

  return (
    <div className="card mt-6 p-5">
      <h2 className="display text-lg">Открыть спор по платежу</h2>
      <textarea
        className="field mt-3 min-h-24 resize-y text-sm"
        placeholder="Опишите, что пошло не так"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      {error && <p className="mt-2 text-sm text-coral-500">{error}</p>}
      <button className="btn btn-primary mt-3 !py-2 text-sm" disabled={busy} onClick={() => void submit()}>
        {busy ? "Отправляем…" : "Отправить в поддержку"}
      </button>
    </div>
  );
}
