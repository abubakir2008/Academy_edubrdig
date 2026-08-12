"use client";

import { useEffect, useState } from "react";

import { TutorsGrid } from "@/components/tutors-grid";
import { get } from "@/lib/api";
import type { Category, TutorCard } from "@/lib/types";

export default function DashboardTutorsPage() {
  const [tutors, setTutors] = useState<TutorCard[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      get<TutorCard[]>("/users/tutors").catch(() => [] as TutorCard[]),
      get<Category[]>("/courses/categories").catch(() => [] as Category[]),
    ]).then(([t, c]) => {
      setTutors(t);
      setCategories(c);
      setLoading(false);
    });
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Репетиторы</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Все репетиторы</h1>
        <p className="mt-2 text-sm text-ink-3">
          Выберите репетитора по специализации и напишите ему напрямую — переписка откроется в
          «Сообщениях».
        </p>
      </header>

      {loading ? <p className="mt-8 text-sm text-ink-3">Загрузка…</p> : <TutorsGrid tutors={tutors} categories={categories} />}
    </div>
  );
}
