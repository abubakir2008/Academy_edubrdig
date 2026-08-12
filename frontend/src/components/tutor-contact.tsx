"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { TutorCard } from "@/lib/types";

/** Primary contact action on a tutor card/profile — adapts to who's looking:
 * a signed-in user can just message the tutor directly (existing chat, no
 * new infrastructure); an anonymous visitor leaves a request instead, since
 * this platform has no self-registration and a lead is the only way staff
 * get their contact info at all. */
export function TutorContact({ tutor, className = "" }: { tutor: TutorCard; className?: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [messaging, setMessaging] = useState(false);
  const [open, setOpen] = useState(false);

  async function writeMessage() {
    setMessaging(true);
    try {
      await post("/chat/conversations", { peer_id: tutor.user_id }, true);
      router.push(`/dashboard/messages?peer=${tutor.user_id}`);
    } catch {
      setMessaging(false);
    }
  }

  if (user) {
    return (
      <button
        className={`btn btn-primary ${className}`}
        disabled={messaging}
        onClick={() => void writeMessage()}
      >
        {messaging ? "Открываем…" : "Написать сообщение"}
      </button>
    );
  }

  return (
    <>
      <button className={`btn btn-primary ${className}`} onClick={() => setOpen(true)}>
        Оставить заявку
      </button>
      {open && <LeadRequestModal tutor={tutor} onClose={() => setOpen(false)} />}
    </>
  );
}

function LeadRequestModal({ tutor, onClose }: { tutor: TutorCard; onClose: () => void }) {
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await post(
        "/leads",
        {
          full_name: fullName.trim(),
          contact_phone: phone.trim() || null,
          contact_email: email.trim() || null,
          preferred_tutor_id: tutor.user_id,
          subject: tutor.full_name ? `Заявка репетитору ${tutor.full_name}` : null,
        },
        false,
      );
      setSubmitted(true);
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) {
        setError("Заявка с этим номером или почтой уже отправлена недавно — мы уже скоро свяжемся с вами.");
      } else {
        setError(e instanceof ApiError ? e.message : "Не удалось отправить заявку. Попробуйте ещё раз.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit = fullName.trim().length > 0 && (phone.trim().length > 0 || email.trim().length > 0);

  return (
    <div
      className="fixed inset-0 z-100 flex items-center justify-center bg-ink/40 px-5"
      onClick={onClose}
      role="presentation"
    >
      <div className="card w-full max-w-md p-6" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal>
        {submitted ? (
          <>
            <h3 className="display text-lg">Спасибо! Заявка отправлена</h3>
            <p className="mt-2 text-sm text-ink-3">
              Мы свяжемся с вами, чтобы договориться о занятиях{tutor.full_name ? ` с ${tutor.full_name}` : ""}.
            </p>
            <button className="btn btn-primary mt-5 w-full" onClick={onClose}>
              Закрыть
            </button>
          </>
        ) : (
          <>
            <h3 className="display text-lg">Заявка{tutor.full_name ? ` репетитору ${tutor.full_name}` : ""}</h3>
            <p className="mt-1 text-sm text-ink-3">
              Оставьте контакты — мы свяжемся и поможем договориться о занятиях.
            </p>
            <div className="mt-4 space-y-3">
              <input
                className="field"
                placeholder="Имя"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
              <input
                className="field"
                placeholder="Телефон"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
              <input
                className="field"
                placeholder="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <p className="text-xs text-ink-3">Укажите хотя бы один способ связи — телефон или почту.</p>
              {error && <p className="text-sm text-coral-500">{error}</p>}
            </div>
            <div className="mt-5 flex gap-2">
              <button
                className="btn btn-primary flex-1"
                disabled={!canSubmit || submitting}
                onClick={() => void submit()}
              >
                {submitting ? "Отправляем…" : "Отправить"}
              </button>
              <button className="btn btn-ghost" onClick={onClose}>
                Отмена
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
