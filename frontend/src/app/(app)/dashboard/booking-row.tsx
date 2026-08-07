"use client";

import Link from "next/link";
import { useState } from "react";

import { API_BASE, post, tokens } from "@/lib/api";
import { money } from "@/lib/format";
import type { Booking, VideoRoom } from "@/lib/types";

import { ReviewForm } from "./review-form";

const STATUS: Record<string, { label: string; tone: string }> = {
  pending: { label: "Ждёт подтверждения", tone: "!bg-citrus-100 !text-citrus-700" },
  confirmed: { label: "Подтверждён", tone: "!bg-jade-100 !text-jade-700" },
  completed: { label: "Проведён", tone: "!bg-aurora-50 !text-aurora-700" },
  cancelled: { label: "Отменён", tone: "!bg-coral-100 !text-coral-500" },
};

/** A call is joinable from 10 minutes before start until it ends. */
function callWindow(booking: Booking): boolean {
  const now = Date.now();
  const start = new Date(booking.scheduled_start).getTime();
  const end = new Date(booking.scheduled_end).getTime();
  return now >= start - 10 * 60_000 && now <= end;
}

export function BookingRow({
  booking,
  asRole,
  muted = false,
  onChanged,
}: {
  booking: Booking;
  asRole: "student" | "tutor";
  muted?: boolean;
  onChanged?: () => void;
}) {
  const [joining, setJoining] = useState(false);
  const [paying, setPaying] = useState(false);
  const [acting, setActing] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewDone, setReviewDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = STATUS[booking.status] ?? { label: booking.status, tone: "" };

  // Awaiting payment: confirmed but never actually paid, and not covered by a
  // prepaid package — see the checkout tab this links to.
  const needsPayment = booking.status !== "cancelled" && !booking.payment_id && !booking.package_id;
  const callHasEnded = Date.now() > new Date(booking.scheduled_end).getTime();

  async function act(action: "confirm" | "cancel" | "complete") {
    setActing(true);
    setError(null);
    try {
      await post(
        `/booking/${booking.id}/${action}`,
        action === "cancel" ? { reason: "Отменено пользователем" } : undefined,
        true,
      );
      onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось выполнить действие");
    } finally {
      setActing(false);
    }
  }

  async function joinCall() {
    if (!booking.lesson_id) return;
    setJoining(true);
    setError(null);
    try {
      const room = await post<VideoRoom>("/video/rooms", { lesson_id: booking.lesson_id }, true);
      window.open(room.join_url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать комнату");
    } finally {
      setJoining(false);
    }
  }

  async function payNow() {
    setPaying(true);
    setError(null);
    try {
      await post("/payments/checkout", { booking_id: booking.id }, true);
      onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Оплата не прошла");
    } finally {
      setPaying(false);
    }
  }

  function downloadIcs() {
    const token = tokens.access();
    // A plain <a href> can't carry an Authorization header, so this opens a
    // tab that the API's own bearer-cookie-less auth would reject — the
    // token travels as a query fallback the backend doesn't parse. Simplest
    // reliable path: fetch with the header, then hand the browser a blob.
    fetch(`${API_BASE}/booking/${booking.id}/ics`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `lesson-${booking.id}.ics`;
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => setError("Не удалось скачать .ics"));
  }

  return (
    <li className={`card p-5 ${muted ? "opacity-70" : ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-semibold">
            {new Date(booking.scheduled_start).toLocaleString("ru-RU", {
              dateStyle: "long",
              timeStyle: "short",
            })}
          </p>
          <p className="mt-1 text-sm text-ink-3">
            {booking.is_trial ? "Пробный урок" : "Урок"} · {booking.duration_minutes} мин ·{" "}
            {booking.package_id ? "оплачено пакетом" : money(booking.price_cents, booking.currency)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <span className={`chip ${status.tone}`}>{status.label}</span>
          <Link href={`/tutors/${booking.tutor_id}`} className="text-sm font-semibold text-aurora-700">
            Профиль
          </Link>
        </div>
      </div>

      {!muted && booking.status !== "cancelled" && (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
          {asRole === "tutor" && booking.status === "pending" && (
            <button className="btn btn-primary !py-2 text-sm" onClick={() => void act("confirm")} disabled={acting}>
              {acting ? "…" : "Подтвердить"}
            </button>
          )}
          {needsPayment && asRole === "student" && (
            <button className="btn btn-primary !py-2 text-sm" onClick={() => void payNow()} disabled={paying}>
              {paying ? "Оплачиваем…" : `Оплатить · ${money(booking.price_cents, booking.currency)}`}
            </button>
          )}
          {booking.lesson_id && callWindow(booking) && (
            <button
              className="btn btn-primary !py-2 text-sm"
              onClick={() => void joinCall()}
              disabled={joining}
              title="Видеозвонок на публичном Jitsi-сервере (meet.jit.si) — для продакшена рекомендуется свой сервер с проверкой токена доступа"
            >
              {joining ? "Открываем…" : "🎥 Войти в звонок"}
            </button>
          )}
          {asRole === "tutor" && booking.status === "confirmed" && callHasEnded && (
            <button className="btn btn-ghost !py-2 text-sm" onClick={() => void act("complete")} disabled={acting}>
              {acting ? "…" : "Отметить проведённым"}
            </button>
          )}
          {booking.lesson_id && (booking.status === "confirmed" || booking.status === "completed") && (
            <Link href={`/dashboard/lessons/${booking.lesson_id}`} className="btn btn-ghost !py-2 text-sm">
              📝 К уроку
            </Link>
          )}
          <button className="btn btn-ghost !py-2 text-sm" onClick={downloadIcs}>
            📅 В календарь
          </button>
          {booking.payment_id && booking.status === "completed" && (
            <Link
              href={`/dashboard/payments?dispute=${booking.payment_id}`}
              className="btn btn-ghost !py-2 text-sm"
            >
              Открыть спор
            </Link>
          )}
          {asRole === "student" && booking.status === "completed" && booking.lesson_id && !reviewDone && (
            <button className="btn btn-ghost !py-2 text-sm" onClick={() => setReviewOpen((v) => !v)}>
              ⭐ Оставить отзыв
            </button>
          )}
          {(booking.status === "pending" || booking.status === "confirmed") && (
            <button
              className="btn btn-ghost !py-2 text-sm text-coral-500"
              onClick={() => void act("cancel")}
              disabled={acting}
            >
              {acting ? "…" : "Отменить"}
            </button>
          )}
        </div>
      )}
      {reviewOpen && booking.lesson_id && (
        <ReviewForm
          tutorId={booking.tutor_id}
          lessonId={booking.lesson_id}
          onDone={() => {
            setReviewOpen(false);
            setReviewDone(true);
          }}
        />
      )}
      {error && <p className="mt-2 text-sm text-coral-500">{error}</p>}
    </li>
  );
}
