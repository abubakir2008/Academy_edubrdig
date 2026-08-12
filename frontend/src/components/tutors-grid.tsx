"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { TutorContact } from "@/components/tutor-contact";
import { initials, pluralRu } from "@/lib/format";
import type { Category, TutorCard } from "@/lib/types";

const PAGE_SIZE = 8;

/** Cycles a few accent colors across chips so a tutor's languages read as
 * distinct badges rather than one grey blob — purely cosmetic, keyed by
 * position so it stays stable across re-renders. */
const CHIP_ACCENTS = [
  "border-aurora-200! bg-aurora-50 text-aurora-700",
  "border-jade-100! bg-jade-100 text-jade-700",
  "border-citrus-100! bg-citrus-100 text-citrus-700",
];

export function TutorsGrid({ tutors, categories }: { tutors: TutorCard[]; categories: Category[] }) {
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const categoryById = useMemo(() => new Map(categories.map((c) => [c.id, c.name])), [categories]);
  const usedCategoryIds = useMemo(
    () => new Set(tutors.flatMap((t) => t.category_ids ?? [])),
    [tutors],
  );
  const filterableCategories = categories.filter((c) => usedCategoryIds.has(c.id));

  const filtered = categoryId ? tutors.filter((t) => t.category_ids?.includes(categoryId)) : tutors;
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages - 1);
  const pageItems = filtered.slice(currentPage * PAGE_SIZE, currentPage * PAGE_SIZE + PAGE_SIZE);

  return (
    <>
      {filterableCategories.length > 0 && (
        <div className="mt-8 flex flex-wrap gap-2">
          <button
            className={`chip ${categoryId === null ? "border-aurora-600! bg-aurora-50 text-aurora-700" : ""}`}
            onClick={() => {
              setCategoryId(null);
              setPage(0);
            }}
          >
            Все
          </button>
          {filterableCategories.map((c) => (
            <button
              key={c.id}
              className={`chip ${categoryId === c.id ? "border-aurora-600! bg-aurora-50 text-aurora-700" : ""}`}
              onClick={() => {
                setCategoryId(c.id);
                setPage(0);
              }}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}

      <div className="mt-6">
        {filtered.length === 0 ? (
          <p className="card p-6 text-sm text-ink-3">Пока нет репетиторов в этой категории.</p>
        ) : (
          <ul className="space-y-4">
            {pageItems.map((t) => (
              <TutorCardItem key={t.user_id} tutor={t} categoryById={categoryById} />
            ))}
          </ul>
        )}

        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-center gap-4">
            <button
              className="btn btn-ghost !py-1.5 text-xs"
              disabled={currentPage === 0}
              onClick={() => setPage(currentPage - 1)}
            >
              ← Назад
            </button>
            <span className="text-xs text-ink-3">
              Стр. {currentPage + 1} из {totalPages} · {filtered.length} всего
            </span>
            <button
              className="btn btn-ghost !py-1.5 text-xs"
              disabled={currentPage === totalPages - 1}
              onClick={() => setPage(currentPage + 1)}
            >
              Дальше →
            </button>
          </div>
        )}
      </div>
    </>
  );
}

function TutorCardItem({ tutor, categoryById }: { tutor: TutorCard; categoryById: Map<string, string> }) {
  const categoryNames = (tutor.category_ids ?? []).map((id) => categoryById.get(id)).filter(Boolean) as string[];
  const languages = tutor.languages ?? [];
  const headline = categoryNames.length ? `Репетитор: ${categoryNames.join(", ")}` : "Репетитор";

  return (
    <li className="card overflow-hidden p-0">
      <div className="flex flex-col gap-5 p-6 sm:flex-row sm:items-start">
        <div className="relative shrink-0 self-center sm:self-start">
          <div className="absolute -inset-1.5 -z-10 rounded-full bg-linear-to-br from-aurora-300 to-citrus-400 opacity-40 blur-sm" />
          {tutor.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={tutor.avatar_url}
              alt={tutor.full_name ?? "Репетитор"}
              className="h-24 w-24 rounded-full border-2 border-paper object-cover shadow-lift sm:h-28 sm:w-28"
            />
          ) : (
            <span className="flex h-24 w-24 items-center justify-center rounded-full border-2 border-paper bg-aurora-100 text-2xl font-semibold text-aurora-700 shadow-lift sm:h-28 sm:w-28">
              {initials(tutor.full_name)}
            </span>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h3 className="display text-xl">{tutor.full_name || "Репетитор"}</h3>
            {tutor.experience_years != null && (
              <span className="text-sm font-semibold text-aurora-700">
                {tutor.experience_years} {pluralRu(tutor.experience_years, ["год", "года", "лет"])} опыта
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm text-ink-3">{headline}</p>

          {tutor.bio_short && (
            <p className="mt-3 rounded-xl border border-aurora-100 bg-aurora-50 px-3.5 py-2.5 text-sm text-aurora-900">
              ✨ {tutor.bio_short}
            </p>
          )}

          {languages.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {languages.map((lang, i) => (
                <span key={lang} className={`chip ${CHIP_ACCENTS[i % CHIP_ACCENTS.length]}`}>
                  {lang}
                </span>
              ))}
            </div>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Link href={`/tutors/${tutor.user_id}`} className="btn btn-ghost !py-2 text-sm">
              Далее →
            </Link>
            <TutorContact tutor={tutor} className="!py-2 text-sm" />
          </div>
        </div>
      </div>
    </li>
  );
}
