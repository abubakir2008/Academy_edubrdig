import Link from "next/link";

import { RatingLine } from "@/components/rating";
import { badgesFor } from "@/lib/badges";
import { countWord, flag, initials, money, toneFor } from "@/lib/format";
import type { TutorSummary } from "@/lib/types";

export function TutorAvatar({
  tutor,
  size = "md",
}: {
  tutor: Pick<TutorSummary, "user_id" | "photo_url" | "headline">;
  size?: "md" | "lg";
}) {
  const box = size === "lg" ? "h-28 w-28 text-3xl" : "h-16 w-16 text-lg";
  if (tutor.photo_url) {
    // Photos come from MinIO / external URLs; plain <img> keeps this dependency-free.
    // eslint-disable-next-line @next/next/no-img-element
    return (
      <img
        src={tutor.photo_url}
        alt={tutor.headline ?? "Репетитор"}
        className={`${box} shrink-0 rounded-2xl object-cover`}
      />
    );
  }
  return (
    <div
      className={`${box} ${toneFor(tutor.user_id)} flex shrink-0 items-center justify-center rounded-2xl font-semibold`}
    >
      {initials(tutor.headline, "EB")}
    </div>
  );
}

export function TutorCard({ tutor }: { tutor: TutorSummary }) {
  const tags = [...tutor.specializations, ...tutor.languages_taught].slice(0, 4);

  return (
    <article className="card group relative flex flex-col gap-4 p-5 transition-all hover:-translate-y-0.5 hover:border-aurora-300 hover:shadow-lift">
      <div className="flex gap-4">
        <TutorAvatar tutor={tutor} />
        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-2">
            <h3 className="display truncate text-lg">
              <Link href={`/tutors/${tutor.user_id}`} className="after:absolute after:inset-0">
                {tutor.headline ?? "Репетитор EduBridge"}
              </Link>
            </h3>
            {tutor.is_verified && (
              <span
                className="mt-1 shrink-0 text-jade-500"
                title="Профиль проверен модерацией"
                aria-label="Проверенный профиль"
              >
                <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
                  <path d="M10 1l2.2 1.6 2.7-.2.9 2.6 2.2 1.6-1 2.6 1 2.6-2.2 1.6-.9 2.6-2.7-.2L10 19l-2.2-1.6-2.7.2-.9-2.6L2 13.4l1-2.6-1-2.6 2.2-1.6.9-2.6 2.7.2L10 1z" />
                  <path
                    d="M6.8 10.2l2.1 2.1 4.3-4.3"
                    stroke="var(--color-paper-2)"
                    strokeWidth="1.8"
                    fill="none"
                    strokeLinecap="round"
                  />
                </svg>
              </span>
            )}
          </div>

          <p className="mt-1 text-sm text-ink-3">
            {flag(tutor.country)} {tutor.native_language ? `Носитель: ${tutor.native_language}` : "Онлайн"}
            {tutor.experience_years > 0 && ` · ${countWord(tutor.experience_years, "year")} опыта`}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <RatingLine rating={tutor.rating} reviews={tutor.total_reviews} />
            {badgesFor(tutor)
              .filter((b) => b.id === "top-rated")
              .map((b) => (
                <span key={b.id} className={`chip ${b.tone}`}>
                  {b.emoji} {b.label}
                </span>
              ))}
          </div>
        </div>
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span key={tag} className="chip">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto flex items-end justify-between gap-3 border-t border-line pt-4">
        <div>
          <p className="display text-xl">{money(tutor.price_cents, tutor.currency)}</p>
          <p className="text-xs text-ink-3">за урок 50 мин</p>
        </div>
        {tutor.trial_price_cents != null && (
          <span className="chip !border-jade-500/30 !bg-jade-100 !text-jade-700">
            Пробный {money(tutor.trial_price_cents, tutor.currency)}
          </span>
        )}
      </div>
    </article>
  );
}

export function TutorCardSkeleton() {
  return (
    <div className="card flex animate-pulse flex-col gap-4 p-5">
      <div className="flex gap-4">
        <div className="h-16 w-16 rounded-2xl bg-line" />
        <div className="flex-1 space-y-2 py-1">
          <div className="h-4 w-2/3 rounded bg-line" />
          <div className="h-3 w-1/2 rounded bg-line" />
          <div className="h-3 w-1/3 rounded bg-line" />
        </div>
      </div>
      <div className="h-12 rounded-xl bg-line/60" />
    </div>
  );
}
