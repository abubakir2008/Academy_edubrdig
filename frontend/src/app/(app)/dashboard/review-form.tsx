"use client";

import { useState } from "react";

import { post } from "@/lib/api";
import type { Review } from "@/lib/types";

export function ReviewForm({
  tutorId,
  lessonId,
  onDone,
}: {
  tutorId: string;
  lessonId: string;
  onDone: () => void;
}) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await post<Review>("/reviews", { tutor_id: tutorId, lesson_id: lessonId, rating, comment: comment || null }, true);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отправить отзыв");
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 space-y-2 border-t border-line pt-3">
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => setRating(n)}
            className={`text-xl leading-none ${n <= rating ? "text-citrus-500" : "text-line"}`}
            aria-label={`${n} из 5`}
          >
            ★
          </button>
        ))}
      </div>
      <textarea
        className="field min-h-16 resize-y text-sm"
        placeholder="Как прошёл урок? (необязательно)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
      />
      {error && <p className="text-sm text-coral-500">{error}</p>}
      <button className="btn btn-primary !py-2 text-sm" disabled={busy} onClick={() => void submit()}>
        {busy ? "Отправляем…" : "Отправить отзыв"}
      </button>
    </div>
  );
}
