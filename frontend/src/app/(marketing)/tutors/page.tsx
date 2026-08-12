import { fetchPublic } from "@/lib/server-api";
import type { Category, TutorCard } from "@/lib/types";

import { TutorsGrid } from "./tutors-grid";

export const metadata = { title: "Репетиторы — EduBridge" };

export default async function TutorsPage() {
  const [tutors, categories] = await Promise.all([
    fetchPublic<TutorCard[]>("/users/tutors", []),
    fetchPublic<Category[]>("/courses/categories", []),
  ]);

  return (
    <div className="mx-auto max-w-6xl px-5 py-10 lg:py-14">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Репетиторы</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Наши преподаватели</h1>
        <p className="mt-3 max-w-2xl text-ink-3">
          Все репетиторы платформы EduBridge — выберите подходящего по специализации, напишите
          напрямую или оставьте заявку, и мы поможем подобрать курс.
        </p>
      </header>

      <TutorsGrid tutors={tutors} categories={categories} />
    </div>
  );
}
