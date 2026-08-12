"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ApiError, del, get, post, put } from "@/lib/api";
import { Paginated } from "@/components/paginated";
import type { Category } from "@/lib/types";

const EMPTY_CREATE = { name: "", slug: "" };
type EditForm = { name: string; slug: string };

function slugify(v: string): string {
  return v
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export default function AdminCategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  const [createForm, setCreateForm] = useState(EMPTY_CREATE);
  const [slugTouched, setSlugTouched] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const list = await get<Category[]>("/courses/categories").catch(() => [] as Category[]);
    setCategories(list);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function createCategory() {
    if (!createForm.name.trim() || !createForm.slug.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await post<Category>("/courses/categories", { name: createForm.name, slug: createForm.slug }, true);
      setCreateForm(EMPTY_CREATE);
      setSlugTouched(false);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось создать категорию");
    } finally {
      setCreating(false);
    }
  }

  function startEdit(c: Category) {
    setEditingId(c.id);
    setEditForm({ name: c.name, slug: c.slug });
    setEditError(null);
  }

  async function saveEdit(id: string) {
    if (!editForm) return;
    setEditError(null);
    try {
      await put(`/courses/categories/${id}`, editForm, true);
      setEditingId(null);
      setEditForm(null);
      await load();
    } catch (e) {
      setEditError(e instanceof ApiError ? e.message : "Не удалось сохранить");
    }
  }

  async function removeCategory(c: Category) {
    if (!window.confirm(`Удалить категорию «${c.name}»? Курсы с этой категорией останутся без категории.`)) return;
    await del(`/courses/categories/${c.id}`).catch(() => undefined);
    await load();
  }

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Админ</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Категории курсов</h1>
        </div>
        <Link href="/dashboard/admin" className="btn btn-ghost">
          ← Панель управления
        </Link>
      </header>

      <section className="mt-8">
        <h2 className="display text-lg">Новая категория</h2>
        <div className="card mt-4 p-6">
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              className="field"
              placeholder="Название (напр. Английский язык)"
              value={createForm.name}
              onChange={(e) => {
                const name = e.target.value;
                setCreateForm((f) => ({ name, slug: slugTouched ? f.slug : slugify(name) }));
              }}
            />
            <input
              className="field font-mono text-sm"
              placeholder="slug (напр. english)"
              value={createForm.slug}
              onChange={(e) => {
                setSlugTouched(true);
                setCreateForm((f) => ({ ...f, slug: slugify(e.target.value) }));
              }}
            />
          </div>
          <p className="mt-2 text-xs text-ink-3">
            Slug — латиницей, только строчные буквы, цифры и дефисы. Заполняется автоматически по названию.
          </p>
          {error && <p className="mt-2 text-xs text-coral-500">{error}</p>}
          <button
            className="btn btn-primary mt-3 !py-2 text-sm"
            onClick={() => void createCategory()}
            disabled={creating}
          >
            {creating ? "Создаём…" : "Создать"}
          </button>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="display text-lg">
          Список <span className="text-sm font-normal text-ink-3">· {categories.length}</span>
        </h2>
        {loading ? (
          <p className="mt-4 text-sm text-ink-3">Загрузка…</p>
        ) : (
          <Paginated
            items={categories}
            empty="Категорий пока нет."
            renderItem={(c) => (
              <li key={c.id} className="card h-full p-4 text-sm">
                {editingId === c.id && editForm ? (
                  <div className="space-y-2">
                    <input
                      className="field text-sm"
                      placeholder="Название"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    />
                    <input
                      className="field font-mono text-sm"
                      placeholder="slug"
                      value={editForm.slug}
                      onChange={(e) => setEditForm({ ...editForm, slug: slugify(e.target.value) })}
                    />
                    {editError && <p className="text-xs text-coral-500">{editError}</p>}
                    <div className="flex gap-2 pt-1">
                      <button className="btn btn-primary !py-1.5 text-xs" onClick={() => void saveEdit(c.id)}>
                        Сохранить
                      </button>
                      <button
                        className="btn btn-ghost !py-1.5 text-xs"
                        onClick={() => {
                          setEditingId(null);
                          setEditError(null);
                        }}
                      >
                        Отмена
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <b className="block truncate font-semibold">{c.name}</b>
                    <p className="mt-0.5 font-mono text-xs text-ink-3">{c.slug}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button className="btn btn-ghost !py-1.5 text-xs" onClick={() => startEdit(c)}>
                        Изменить
                      </button>
                      <button
                        className="btn btn-ghost !py-1.5 text-xs text-coral-500"
                        onClick={() => void removeCategory(c)}
                      >
                        Удалить
                      </button>
                    </div>
                  </>
                )}
              </li>
            )}
          />
        )}
      </section>
    </div>
  );
}
