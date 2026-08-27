"use client";

import { useCallback, useEffect, useState } from "react";

import { del, get, post, put } from "@/lib/api";
import type { Article, Language } from "@/lib/types";

const TYPES: Article["type"][] = ["blog", "faq", "page", "policy", "landing"];

const EMPTY = { slug: "", type: "blog" as Article["type"], title: "", body: "", published: false };

export default function CmsPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newLang, setNewLang] = useState({ code: "", name: "" });

  const [locale, setLocale] = useState("ru");
  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [translationDrafts, setTranslationDrafts] = useState<Record<string, string>>({});
  const [newKey, setNewKey] = useState({ key: "", value: "" });

  const load = useCallback(async () => {
    const [arts, langs] = await Promise.all([
      get<Article[]>("/cms/articles?limit=100", true).catch(() => [] as Article[]),
      get<Language[]>("/localization/languages", true).catch(() => [] as Language[]),
    ]);
    setArticles(arts);
    setLanguages(langs);
  }, []);

  const loadTranslations = useCallback(async (forLocale: string) => {
    const t = await get<Record<string, string>>(`/localization/translations?locale=${forLocale}`, true).catch(
      () => ({}) as Record<string, string>,
    );
    setTranslations(t);
    setTranslationDrafts(t);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadTranslations(locale);
  }, [locale, loadTranslations]);

  async function saveTranslation(key: string) {
    const value = translationDrafts[key] ?? "";
    await put("/localization/translations", { locale, key, value }, true).catch(() => undefined);
    await loadTranslations(locale);
  }

  async function addTranslation() {
    if (!newKey.key.trim()) return;
    await put("/localization/translations", { locale, key: newKey.key, value: newKey.value }, true).catch(
      () => undefined,
    );
    setNewKey({ key: "", value: "" });
    await loadTranslations(locale);
  }

  function edit(a: Article) {
    setEditingId(a.id);
    setForm({ slug: a.slug, type: a.type, title: a.title, body: a.body, published: a.published });
  }

  async function save() {
    setError(null);
    try {
      if (editingId) {
        await put(`/cms/articles/${editingId}`, {
          title: form.title, body: form.body, published: form.published,
        }, true);
      } else {
        await post("/cms/articles", form, true);
      }
      setForm(EMPTY);
      setEditingId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить");
    }
  }

  async function remove(id: string) {
    setError(null);
    try {
      await del(`/cms/articles/${id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось удалить запись");
    }
  }

  async function addLanguage() {
    if (!newLang.code || !newLang.name) return;
    await post("/localization/languages", { code: newLang.code, name: newLang.name, is_active: true }, true).catch(
      () => undefined,
    );
    setNewLang({ code: "", name: "" });
    await load();
  }

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Контент</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">CMS и языки</h1>
      </header>

      <section className="card mt-8 p-6">
        <h2 className="display text-lg">{editingId ? "Редактировать статью" : "Новая статья"}</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <input
            className="field"
            placeholder="Slug (URL)"
            value={form.slug}
            disabled={!!editingId}
            onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value }))}
          />
          <select
            className="field"
            value={form.type}
            disabled={!!editingId}
            onChange={(e) => setForm((f) => ({ ...f, type: e.target.value as Article["type"] }))}
          >
            {TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <input
            className="field sm:col-span-2"
            placeholder="Заголовок"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          />
          <textarea
            className="field min-h-32 resize-y sm:col-span-2"
            placeholder="Текст"
            value={form.body}
            onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
          />
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={form.published}
              onChange={(e) => setForm((f) => ({ ...f, published: e.target.checked }))}
            />
            Опубликовано
          </label>
        </div>
        {error && <p className="mt-2 text-sm text-coral-500">{error}</p>}
        <div className="mt-4 flex gap-2">
          <button className="btn btn-primary !py-2 text-sm" onClick={() => void save()}>
            {editingId ? "Сохранить" : "Создать"}
          </button>
          {editingId && (
            <button
              className="btn btn-ghost !py-2 text-sm"
              onClick={() => {
                setEditingId(null);
                setForm(EMPTY);
              }}
            >
              Отмена
            </button>
          )}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="display text-lg">Статьи ({articles.length})</h2>
        <ul className="mt-4 space-y-2">
          {articles.map((a) => (
            <li key={a.id} className="card flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-semibold">{a.title}</p>
                <p className="text-xs text-ink-3">
                  /{a.slug} · {a.type} · {a.published ? "опубликовано" : "черновик"}
                </p>
              </div>
              <div className="flex gap-2">
                <button className="btn btn-ghost !py-1.5 text-xs" onClick={() => edit(a)}>
                  Редактировать
                </button>
                <button className="btn btn-ghost !py-1.5 text-xs text-coral-500" onClick={() => void remove(a.id)}>
                  Удалить
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="card mt-8 p-6">
        <h2 className="display text-lg">Языки платформы</h2>
        <ul className="mt-3 flex flex-wrap gap-2">
          {languages.map((l) => (
            <span key={l.code} className="chip">{l.name} ({l.code})</span>
          ))}
        </ul>
        <div className="mt-4 flex gap-2">
          <input className="field w-24" placeholder="ru" value={newLang.code} onChange={(e) => setNewLang((f) => ({ ...f, code: e.target.value }))} />
          <input className="field flex-1" placeholder="Русский" value={newLang.name} onChange={(e) => setNewLang((f) => ({ ...f, name: e.target.value }))} />
          <button className="btn btn-primary !py-2 text-sm" onClick={() => void addLanguage()}>
            Добавить
          </button>
        </div>
      </section>

      <section className="card mt-8 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="display text-lg">Переводы интерфейса</h2>
          <select className="field !w-32" value={locale} onChange={(e) => setLocale(e.target.value)}>
            {(languages.length ? languages.map((l) => l.code) : ["ru"]).map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </div>
        <p className="mt-1 text-sm text-ink-3">
          Строки для этой локали. Пока ни одна страница сайта не читает их динамически — тексты в
          интерфейсе захардкожены на русском, это склад ключей на будущее.
        </p>
        {Object.keys(translations).length > 0 ? (
          <ul className="mt-4 space-y-2">
            {Object.entries(translations).map(([key]) => (
              <li key={key} className="flex flex-wrap items-center gap-2">
                <span className="w-40 shrink-0 truncate text-xs text-ink-3" title={key}>
                  {key}
                </span>
                <input
                  className="field flex-1"
                  value={translationDrafts[key] ?? ""}
                  onChange={(e) => setTranslationDrafts((d) => ({ ...d, [key]: e.target.value }))}
                />
                <button
                  className="btn btn-ghost !py-1.5 text-xs"
                  disabled={translationDrafts[key] === translations[key]}
                  onClick={() => void saveTranslation(key)}
                >
                  Сохранить
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm text-ink-3">Переводов для «{locale}» пока нет.</p>
        )}
        <div className="mt-4 flex gap-2">
          <input
            className="field w-40"
            placeholder="ключ"
            value={newKey.key}
            onChange={(e) => setNewKey((f) => ({ ...f, key: e.target.value }))}
          />
          <input
            className="field flex-1"
            placeholder="значение"
            value={newKey.value}
            onChange={(e) => setNewKey((f) => ({ ...f, value: e.target.value }))}
          />
          <button className="btn btn-primary !py-2 text-sm" onClick={() => void addTranslation()}>
            Добавить
          </button>
        </div>
      </section>
    </div>
  );
}
