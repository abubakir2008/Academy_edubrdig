"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { get, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Course } from "@/lib/types";

const EMPTY = { title: "", description: "" };

export default function CoursesPage() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [form, setForm] = useState(EMPTY);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSuperAdmin = user?.role === "super_admin";
  const isStaff = user?.role === "admin" || isSuperAdmin;

  const load = useCallback(async () => {
    if (!user) return;
    const path = isStaff ? "/courses?limit=100" : "/courses/me";
    const items = await get<Course[]>(path, true).catch(() => [] as Course[]);
    setCourses(items);
  }, [user, isStaff]);

  useEffect(() => {
    void load();
  }, [load]);

  async function createCourse() {
    if (!form.title.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await post("/courses", { title: form.title, description: form.description || null }, true);
      setForm(EMPTY);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать курс");
    } finally {
      setCreating(false);
    }
  }

  if (!user) return null;

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Курсы</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">
          {isStaff ? "Все курсы" : "Мои курсы"}
        </h1>
      </header>

      {isSuperAdmin && (
        <section className="card mt-8 p-6">
          <h2 className="display text-lg">Новый курс</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <input
              className="field"
              placeholder="Название"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
            <input
              className="field"
              placeholder="Описание (необязательно)"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          {error && <p className="mt-2 text-sm text-coral-500">{error}</p>}
          <button
            className="btn btn-primary mt-4 !py-2 text-sm"
            disabled={creating}
            onClick={() => void createCourse()}
          >
            {creating ? "Создаём…" : "Создать"}
          </button>
        </section>
      )}

      <section className="mt-8">
        <h2 className="display text-lg">Список ({courses.length})</h2>
        <ul className="mt-4 space-y-2">
          {courses.map((c) => (
            <li key={c.id} className="card flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-semibold">{c.title}</p>
                {c.description && <p className="text-xs text-ink-3">{c.description}</p>}
              </div>
              <div className="flex gap-2">
                {isStaff && (
                  <Link href={`/dashboard/courses/${c.id}`} className="btn btn-ghost !py-1.5 text-xs">
                    Открыть
                  </Link>
                )}
                <Link href={`/dashboard/courses/${c.id}/calendar`} className="btn btn-ghost !py-1.5 text-xs">
                  Уроки и календарь
                </Link>
              </div>
            </li>
          ))}
          {courses.length === 0 && <p className="card p-6 text-sm text-ink-3">Курсов пока нет.</p>}
        </ul>
      </section>
    </div>
  );
}
