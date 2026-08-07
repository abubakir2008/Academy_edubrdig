import Link from "next/link";
import { notFound } from "next/navigation";

import { RatingLine, Stars } from "@/components/rating";
import { TutorAvatar } from "@/components/tutor-card";
import { badgesFor } from "@/lib/badges";
import { clock, countWord, flag, money, weekday } from "@/lib/format";
import { fetchPublic } from "@/lib/server-api";
import type { Review, TutorDetail } from "@/lib/types";

import { BookingPanel } from "./booking-panel";
import { FavoriteButton } from "./favorite-button";

type Params = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Params) {
  const { id } = await params;
  const tutor = await fetchPublic<TutorDetail | null>(`/tutors/${id}`, null);
  return { title: tutor?.headline ?? "Репетитор" };
}

export default async function TutorPage({ params }: Params) {
  const { id } = await params;
  const tutor = await fetchPublic<TutorDetail | null>(`/tutors/${id}`, null);
  if (!tutor) notFound();

  const reviews = await fetchPublic<Review[]>(`/reviews/tutor/${id}?limit=10`, []);

  return (
    <div className="mx-auto max-w-7xl px-5 py-10">
      <nav className="mb-6 text-sm text-ink-3">
        <Link href="/tutors" className="hover:text-ink">
          Каталог
        </Link>
        <span className="mx-2">/</span>
        <span>{tutor.headline ?? "Репетитор"}</span>
      </nav>

      <div className="grid gap-10 lg:grid-cols-[1fr_340px]">
        <div>
          <header className="flex flex-wrap items-start gap-6">
            <TutorAvatar tutor={tutor} size="lg" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="display text-[clamp(1.8rem,3.5vw,2.6rem)]">
                  {tutor.headline ?? "Репетитор EduBridge"}
                </h1>
                {tutor.is_verified && (
                  <span className="chip !border-jade-500/30 !bg-jade-100 !text-jade-700">
                    Профиль проверен
                  </span>
                )}
                {badgesFor(tutor)
                  .filter((b) => b.id !== "verified")
                  .map((b) => (
                    <span key={b.id} className={`chip ${b.tone}`}>
                      {b.emoji} {b.label}
                    </span>
                  ))}
              </div>

              <p className="mt-2 text-ink-3">
                {flag(tutor.country)}{" "}
                {tutor.native_language ? `Носитель: ${tutor.native_language}` : "Онлайн-занятия"}
                {tutor.experience_years > 0 &&
                  ` · ${countWord(tutor.experience_years, "year")} опыта`}
                {tutor.total_lessons > 0 && ` · ${countWord(tutor.total_lessons, "lesson")} проведено`}
              </p>

              <div className="mt-3">
                <RatingLine rating={tutor.rating} reviews={tutor.total_reviews} />
              </div>

              <div className="mt-4 flex flex-wrap gap-1.5">
                {[...tutor.specializations, ...tutor.languages_taught].map((tag) => (
                  <span key={tag} className="chip">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </header>

          {tutor.video_url && (
            <section className="mt-10">
              <h2 className="display text-xl">Видео-визитка</h2>
              <a
                href={tutor.video_url}
                target="_blank"
                rel="noreferrer"
                className="card mt-3 flex items-center gap-3 p-5 transition-colors hover:border-aurora-300"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-aurora-600 text-white">
                  ▶
                </span>
                <span className="text-sm font-medium">Смотреть видео репетитора</span>
              </a>
            </section>
          )}

          {tutor.description && (
            <section className="mt-10">
              <h2 className="display text-xl">О репетиторе</h2>
              <p className="mt-3 whitespace-pre-line leading-relaxed text-ink-2">
                {tutor.description}
              </p>
            </section>
          )}

          {tutor.certificates.length > 0 && (
            <section className="mt-10">
              <h2 className="display text-xl">Образование и сертификаты</h2>
              <ul className="mt-4 space-y-3">
                {tutor.certificates.map((cert) => (
                  <li key={cert.id} className="card flex items-start gap-3 p-4">
                    <span className="text-lg" aria-hidden>
                      🎓
                    </span>
                    <div>
                      <p className="font-semibold">{cert.title}</p>
                      <p className="text-sm text-ink-3">
                        {[cert.issued_by, cert.year].filter(Boolean).join(" · ") || "—"}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {tutor.working_hours.length > 0 && (
            <section className="mt-10">
              <h2 className="display text-xl">Расписание</h2>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {[...tutor.working_hours]
                  .sort((a, b) => a.weekday - b.weekday || a.start_time.localeCompare(b.start_time))
                  .map((slot) => (
                    <div
                      key={slot.id}
                      className="flex items-center justify-between rounded-xl border border-line bg-paper-2 px-4 py-2.5 text-sm"
                    >
                      <span className="font-semibold">{weekday(slot.weekday)}</span>
                      <span className="text-ink-3">
                        {clock(slot.start_time)} — {clock(slot.end_time)}
                      </span>
                    </div>
                  ))}
              </div>
            </section>
          )}

          <section className="mt-10">
            <h2 className="display text-xl">
              Отзывы {tutor.total_reviews > 0 && <span className="text-ink-3">· {tutor.total_reviews}</span>}
            </h2>
            {reviews.length > 0 ? (
              <ul className="mt-4 space-y-3">
                {reviews.map((review) => (
                  <li key={review.id} className="card p-5">
                    <div className="flex items-center justify-between gap-3">
                      <Stars value={review.rating} />
                      <time className="text-xs text-ink-3" dateTime={review.created_at}>
                        {new Date(review.created_at).toLocaleDateString("ru-RU")}
                      </time>
                    </div>
                    {review.comment && (
                      <p className="mt-3 leading-relaxed text-ink-2">{review.comment}</p>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-ink-3">
                Отзывов пока нет — вы можете стать первым учеником.
              </p>
            )}
          </section>
        </div>

        <aside className="lg:sticky lg:top-28 lg:self-start">
          <div className="card p-6 shadow-lift">
            <div className="flex items-end justify-between">
              <div>
                <p className="display text-3xl">{money(tutor.price_cents, tutor.currency)}</p>
                <p className="text-sm text-ink-3">за урок 50 мин</p>
              </div>
              <FavoriteButton tutorId={tutor.user_id} />
            </div>

            {tutor.trial_price_cents != null && (
              <p className="mt-3 rounded-xl bg-jade-100 px-3 py-2 text-sm text-jade-700">
                Пробный урок — {money(tutor.trial_price_cents, tutor.currency)}
              </p>
            )}

            <BookingPanel tutor={tutor} />

            <p className="mt-4 text-xs leading-relaxed text-ink-3">
              Оплата проходит на площадке. Если урок не состоялся — деньги возвращаются по правилам
              EduBridge.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
