"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { get, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Category, Course } from "@/lib/types";

const EMPTY = { title: "", description: "", category_id: "" };

export default function CoursesPage() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
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

  useEffect(() => {
    get<Category[]>("/courses/categories")
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  const categoryName = (id: string | null) => categories.find((c) => c.id === id)?.name ?? null;

  async function createCourse() {
    if (!form.title.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await post(
        "/courses",
        { title: form.title, description: form.description || null, category_id: form.category_id || null },
        true,
      );
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
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Курсы</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">
            {isStaff ? "Все курсы" : "Мои курсы"}
          </h1>
        </div>
        {isStaff && (
          <Link href="/dashboard/admin/categories" className="btn btn-ghost">
            Категории курсов →
          </Link>
        )}
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
            <select
              className="field"
              value={form.category_id}
              onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
            >
              <option value="">Без категории</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <input
              className="field sm:col-span-2"
              placeholder="Описание (необязательно)"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          {categories.length === 0 && (
            <p className="mt-2 text-xs text-ink-3">
              Категорий пока нет —{" "}
              <Link href="/dashboard/admin/categories" className="font-semibold text-aurora-700">
                создайте их здесь
              </Link>
              .
            </p>
          )}
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
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold">{c.title}</p>
                  {categoryName(c.category_id) && <span className="chip">{categoryName(c.category_id)}</span>}
                </div>
                {c.description && <p className="text-xs text-ink-3">{c.description}</p>}
              </div>
              <div className="flex gap-2">
                {(isStaff || user?.role === "tutor") && (
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
