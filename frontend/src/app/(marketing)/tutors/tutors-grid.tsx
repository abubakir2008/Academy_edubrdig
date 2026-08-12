"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Paginated } from "@/components/paginated";
import { TutorContact } from "@/components/tutor-contact";
import { initials, pluralRu } from "@/lib/format";
import type { Category, TutorCard } from "@/lib/types";

export function TutorsGrid({ tutors, categories }: { tutors: TutorCard[]; categories: Category[] }) {
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const categoryById = useMemo(() => new Map(categories.map((c) => [c.id, c.name])), [categories]);
  const usedCategoryIds = useMemo(
    () => new Set(tutors.flatMap((t) => t.category_ids ?? [])),
    [tutors],
  );
  const filterableCategories = categories.filter((c) => usedCategoryIds.has(c.id));

  const filtered = categoryId ? tutors.filter((t) => t.category_ids?.includes(categoryId)) : tutors;

  return (
    <>
      {filterableCategories.length > 0 && (
        <div className="mt-8 flex flex-wrap gap-2">
          <button
            className={`chip ${categoryId === null ? "border-aurora-600! bg-aurora-50 text-aurora-700" : ""}`}
            onClick={() => setCategoryId(null)}
          >
            Все
          </button>
          {filterableCategories.map((c) => (
            <button
              key={c.id}
              className={`chip ${categoryId === c.id ? "border-aurora-600! bg-aurora-50 text-aurora-700" : ""}`}
              onClick={() => setCategoryId(c.id)}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}

      <div className="mt-6">
        <Paginated
          items={filtered}
          empty="Пока нет репетиторов в этой категории."
          pageSize={9}
          renderItem={(t) => <TutorCardItem key={t.user_id} tutor={t} categoryById={categoryById} />}
        />
      </div>
    </>
  );
}

function TutorCardItem({ tutor, categoryById }: { tutor: TutorCard; categoryById: Map<string, string> }) {
  const categoryNames = (tutor.category_ids ?? []).map((id) => categoryById.get(id)).filter(Boolean) as string[];
  const languageCount = tutor.languages?.length ?? 0;

  return (
    <li className="card flex h-full flex-col p-5">
      <div className="flex items-center gap-3">
        {tutor.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={tutor.avatar_url}
            alt={tutor.full_name ?? "Репетитор"}
            className="h-14 w-14 shrink-0 rounded-full object-cover"
          />
        ) : (
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-aurora-100 text-lg font-semibold text-aurora-700">
            {initials(tutor.full_name)}
          </span>
        )}
        <div className="min-w-0">
          <p className="truncate font-semibold">{tutor.full_name || "Репетитор"}</p>
          {tutor.experience_years != null && (
            <p className="text-xs text-ink-3">
              {tutor.experience_years} {pluralRu(tutor.experience_years, ["год", "года", "лет"])} опыта
            </p>
          )}
        </div>
      </div>

      {categoryNames.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {categoryNames.map((name) => (
            <span key={name} className="chip">
              {name}
            </span>
          ))}
        </div>
      )}

      {tutor.bio_short && <p className="mt-3 line-clamp-3 text-sm text-ink-2">{tutor.bio_short}</p>}

      {languageCount > 0 && (
        <p className="mt-3 text-xs text-ink-3">
          Говорит на {languageCount} {pluralRu(languageCount, ["языке", "языках", "языках"])}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2 pt-1">
        <Link href={`/tutors/${tutor.user_id}`} className="btn btn-ghost !py-1.5 text-xs">
          Далее →
        </Link>
        <TutorContact tutor={tutor} className="!py-1.5 text-xs" />
      </div>
    </li>
  );
}
