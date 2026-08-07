/**
 * Tutor badges/levels — computed client-side from fields the backend already
 * returns (rating, total_reviews, total_lessons, experience_years,
 * is_verified). No new backend endpoint: a badge is a read of existing data,
 * not a new fact the platform needs to store.
 */

import type { TutorSummary } from "./types";

export type Badge = { id: string; label: string; emoji: string; tone: string };

export function badgesFor(t: Pick<
  TutorSummary,
  "is_verified" | "rating" | "total_reviews" | "total_lessons" | "experience_years"
>): Badge[] {
  const badges: Badge[] = [];

  if (t.is_verified) {
    badges.push({ id: "verified", label: "Проверенный профиль", emoji: "🛡️", tone: "!bg-jade-100 !text-jade-700" });
  }
  if (t.rating >= 4.8 && t.total_reviews >= 5) {
    badges.push({ id: "top-rated", label: "Топ рейтинг", emoji: "⭐", tone: "!bg-citrus-100 !text-citrus-700" });
  }
  if (t.total_lessons >= 100) {
    badges.push({ id: "veteran", label: `${t.total_lessons}+ уроков`, emoji: "🏅", tone: "!bg-aurora-50 !text-aurora-700" });
  } else if (t.total_lessons >= 20) {
    badges.push({ id: "experienced", label: `${t.total_lessons}+ уроков на платформе`, emoji: "📈", tone: "!bg-aurora-50 !text-aurora-700" });
  }
  if (t.experience_years >= 10) {
    badges.push({ id: "veteran-teacher", label: `${t.experience_years} лет опыта`, emoji: "🎓", tone: "!bg-coral-100 !text-coral-500" });
  }

  return badges;
}

/** A single headline level, for compact display (tutor card, dashboard). */
export function levelFor(t: Pick<TutorSummary, "rating" | "total_lessons">): string {
  if (t.total_lessons >= 100 && t.rating >= 4.7) return "Мастер";
  if (t.total_lessons >= 20) return "Опытный";
  if (t.total_lessons > 0) return "Активный";
  return "Новичок";
}
