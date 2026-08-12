import Link from "next/link";
import { notFound } from "next/navigation";

import { TutorContact } from "@/components/tutor-contact";
import { initials, pluralRu } from "@/lib/format";
import { fetchPublic } from "@/lib/server-api";
import type { Category, TutorDetail } from "@/lib/types";

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

  return (
    <div className="mx-auto max-w-3xl px-5 py-10 lg:py-14">
      <nav className="mb-6 text-sm text-ink-3">
        <Link href="/tutors" className="hover:text-ink">
          Репетиторы
        </Link>
        <span className="mx-2">/</span>
        <span>{tutor.full_name || "Репетитор"}</span>
      </nav>

      <div className="card p-6 sm:p-8">
        <div className="flex flex-wrap items-center gap-4">
          {tutor.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={tutor.avatar_url}
              alt={tutor.full_name ?? "Репетитор"}
              className="h-20 w-20 shrink-0 rounded-full object-cover"
            />
          ) : (
            <span className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-aurora-100 text-2xl font-semibold text-aurora-700">
              {initials(tutor.full_name)}
            </span>
          )}
          <div>
            <h1 className="display text-2xl">{tutor.full_name || "Репетитор"}</h1>
            {tutor.experience_years != null && (
              <p className="mt-1 text-sm text-ink-3">
                {tutor.experience_years} {pluralRu(tutor.experience_years, ["год", "года", "лет"])} опыта
              </p>
            )}
          </div>
        </div>

        {categoryNames.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-1.5">
            {categoryNames.map((name) => (
              <span key={name} className="chip">
                {name}
              </span>
            ))}
          </div>
        )}

        {tutor.languages && tutor.languages.length > 0 && (
          <p className="mt-4 text-sm text-ink-2">
            <b className="font-semibold">Языки:</b> {tutor.languages.join(", ")}
          </p>
        )}

        {tutor.bio_short && <p className="mt-4 text-sm font-medium text-ink-2">{tutor.bio_short}</p>}

        {tutor.bio_full && (
          <div className="mt-6 whitespace-pre-line text-sm leading-relaxed text-ink-2">{tutor.bio_full}</div>
        )}

        <div className="mt-8">
          <TutorContact tutor={tutor} />
        </div>
      </div>
    </div>
  );
}
