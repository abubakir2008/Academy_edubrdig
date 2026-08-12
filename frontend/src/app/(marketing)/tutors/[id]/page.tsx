import Link from "next/link";
import { notFound } from "next/navigation";

import { TutorContact } from "@/components/tutor-contact";
import { initials, pluralRu } from "@/lib/format";
import { fetchPublic } from "@/lib/server-api";
import type { Category, TutorDetail } from "@/lib/types";

const CHIP_ACCENTS = [
  "border-aurora-200! bg-aurora-50 text-aurora-700",
  "border-jade-100! bg-jade-100 text-jade-700",
  "border-citrus-100! bg-citrus-100 text-citrus-700",
];

type Params = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Params) {
  const { id } = await params;
  const tutor = await fetchPublic<TutorDetail | null>(`/users/tutors/${id}`, null);
  return { title: tutor ? `${tutor.full_name ?? "Репетитор"} — EduBridge` : "Репетитор" };
}

export default async function TutorProfilePage({ params }: Params) {
  const { id } = await params;
  const [tutor, categories] = await Promise.all([
    fetchPublic<TutorDetail | null>(`/users/tutors/${id}`, null),
    fetchPublic<Category[]>("/courses/categories", []),
  ]);
  if (!tutor) notFound();

  const categoryById = new Map(categories.map((c) => [c.id, c.name]));
  const categoryNames = (tutor.category_ids ?? []).map((cid) => categoryById.get(cid)).filter(Boolean) as string[];
  const headline = categoryNames.length ? `Репетитор: ${categoryNames.join(", ")}` : "Репетитор";
  const languages = tutor.languages ?? [];

  return (
    <div className="mx-auto max-w-3xl px-5 py-10 lg:py-14">
      <nav className="mb-6 text-sm text-ink-3">
        <Link href="/tutors" className="hover:text-ink">
          Репетиторы
        </Link>
        <span className="mx-2">/</span>
        <span>{tutor.full_name || "Репетитор"}</span>
      </nav>

      <div className="card overflow-hidden p-0">
        <div className="bg-linear-to-br from-aurora-50 via-paper to-citrus-100/40 p-6 sm:p-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:items-center sm:text-left">
              <div className="relative shrink-0">
                <div className="absolute -inset-2 -z-10 rounded-full bg-linear-to-br from-aurora-300 to-citrus-400 opacity-40 blur-md" />
                {tutor.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={tutor.avatar_url}
                    alt={tutor.full_name ?? "Репетитор"}
                    className="h-28 w-28 rounded-full border-2 border-paper object-cover shadow-lift"
                  />
                ) : (
                  <span className="flex h-28 w-28 items-center justify-center rounded-full border-2 border-paper bg-aurora-100 text-3xl font-semibold text-aurora-700 shadow-lift">
                    {initials(tutor.full_name)}
                  </span>
                )}
              </div>
              <div>
                <h1 className="display text-2xl">{tutor.full_name || "Репетитор"}</h1>
                <p className="mt-1 text-sm text-ink-3">{headline}</p>
                {tutor.experience_years != null && (
                  <span className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-paper px-3 py-1 text-sm font-semibold text-aurora-700 shadow-sm">
                    {tutor.experience_years} {pluralRu(tutor.experience_years, ["год", "года", "лет"])} опыта
                  </span>
                )}
              </div>
            </div>

            <div className="shrink-0">
              <TutorContact tutor={tutor} className="w-full sm:w-auto" />
            </div>
          </div>

          {categoryNames.length > 0 && (
            <div className="mt-5 flex flex-wrap justify-center gap-1.5 sm:justify-start">
              {categoryNames.map((name) => (
                <span key={name} className="chip border-aurora-200! bg-paper">
                  {name}
                </span>
              ))}
            </div>
          )}

          {tutor.bio_short && (
            <p className="mt-4 rounded-xl border border-aurora-100 bg-paper/80 px-4 py-3 text-sm text-aurora-900">
              ✨ {tutor.bio_short}
            </p>
          )}
        </div>

        <div className="p-6 sm:p-8">
          {tutor.bio_full && (
            <section>
              <h2 className="display text-lg">Обо мне</h2>
              <div className="mt-3 whitespace-pre-line text-sm leading-relaxed text-ink-2">{tutor.bio_full}</div>
            </section>
          )}

          {languages.length > 0 && (
            <section className={tutor.bio_full ? "mt-8" : ""}>
              <h2 className="display text-lg">Владею языками</h2>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {languages.map((lang, i) => (
                  <span key={lang} className={`chip ${CHIP_ACCENTS[i % CHIP_ACCENTS.length]}`}>
                    {lang}
                  </span>
                ))}
              </div>
            </section>
          )}

          {!tutor.bio_full && languages.length === 0 && (
            <p className="text-sm text-ink-3">Репетитор ещё не заполнил подробную анкету.</p>
          )}
        </div>
      </div>
    </div>
  );
}
