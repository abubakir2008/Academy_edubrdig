"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { TutorCard, TutorCardSkeleton } from "@/components/tutor-card";
import { get, qs } from "@/lib/api";
import { CATEGORIES } from "@/lib/catalog";
import { DEFAULT_CURRENCY, countWord, money } from "@/lib/format";
import type { TutorQuery, TutorSummary } from "@/lib/types";

const PAGE_SIZE = 12;

const SORTS: { id: NonNullable<TutorQuery["sort"]>; label: string }[] = [
  { id: "rating", label: "По рейтингу" },
  { id: "reviews", label: "По количеству отзывов" },
  { id: "price_asc", label: "Сначала дешевле" },
  { id: "price_desc", label: "Сначала дороже" },
  { id: "experience", label: "По опыту" },
];

const LANGUAGE_CATEGORY = CATEGORIES.find((c) => c.mapsTo === "language")!;

/** Everything the backend can filter on, mirrored from the URL. */
type Filters = {
  q: string;
  category: string;
  language: string;
  max_price_cents: string;
  min_rating: string;
  min_experience: string;
  native_speaker: boolean;
  has_trial: boolean;
  verified_only: boolean;
  sort: NonNullable<TutorQuery["sort"]>;
};

const EMPTY: Filters = {
  q: "",
  category: "",
  language: "",
  max_price_cents: "",
  min_rating: "",
  min_experience: "",
  native_speaker: false,
  has_trial: false,
  verified_only: false,
  sort: "rating",
};

export function TutorCatalog() {
  const router = useRouter();
  const params = useSearchParams();
  const fromWizard = params.get("from") === "wizard";

  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [tutors, setTutors] = useState<TutorSummary[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exhausted, setExhausted] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);

  // URL is the source of truth: shareable links, back button, wizard hand-off.
  useEffect(() => {
    setFilters({
      q: params.get("q") ?? "",
      category: params.get("category") ?? "",
      language: params.get("language") ?? "",
      max_price_cents: params.get("max_price_cents") ?? "",
      min_rating: params.get("min_rating") ?? "",
      min_experience: params.get("min_experience") ?? "",
      native_speaker: params.get("native_speaker") === "true",
      has_trial: params.get("has_trial") === "true",
      verified_only: params.get("verified_only") === "true",
      sort: (params.get("sort") as Filters["sort"]) ?? "rating",
    });
    setPage(0);
  }, [params]);

  const query = useMemo<TutorQuery>(
    () => ({
      q: filters.q || undefined,
      category: filters.category || undefined,
      language: filters.language || undefined,
      max_price_cents: filters.max_price_cents ? Number(filters.max_price_cents) : undefined,
      min_rating: filters.min_rating ? Number(filters.min_rating) : undefined,
      min_experience: filters.min_experience ? Number(filters.min_experience) : undefined,
      native_speaker: filters.native_speaker || undefined,
      has_trial: filters.has_trial || undefined,
      verified_only: filters.verified_only || undefined,
      sort: filters.sort,
    }),
    [filters],
  );

  const load = useCallback(
    async (targetPage: number) => {
      setLoading(true);
      setError(null);
      try {
        const data = await get<TutorSummary[]>(
          `/tutors${qs({ ...query, limit: PAGE_SIZE, offset: targetPage * PAGE_SIZE })}`,
        );
        setExhausted(data.length < PAGE_SIZE);
        setTutors((prev) => (targetPage === 0 ? data : [...prev, ...data]));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Не удалось загрузить репетиторов");
        if (targetPage === 0) setTutors([]);
      } finally {
        setLoading(false);
      }
    },
    [query],
  );

  useEffect(() => {
    void load(page);
  }, [load, page]);

  /** Writing to the URL re-triggers the effect above, which reloads results. */
  function apply(patch: Partial<Filters>) {
    const next = { ...filters, ...patch };
    const clean: Record<string, string | number | boolean | undefined> = {
      ...next,
      sort: next.sort === "rating" ? undefined : next.sort,
    };
    router.replace(`/tutors${qs(clean)}`, { scroll: false });
  }

  const activeCount = Object.entries(filters).filter(
    ([key, value]) => key !== "sort" && value !== "" && value !== false,
  ).length;

  return (
    <div className="mx-auto max-w-7xl px-5 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="display text-[clamp(2rem,4vw,3rem)]">Репетиторы</h1>
          <p className="mt-2 text-ink-3">
            {loading && page === 0
              ? "Ищем подходящих…"
              : `${countWord(tutors.length, "tutor")}${exhausted ? "" : " и ещё"} по вашим фильтрам`}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="label !mb-0 hidden sm:block" htmlFor="sort">
            Сортировка
          </label>
          <select
            id="sort"
            className="field !w-auto"
            value={filters.sort}
            onChange={(e) => apply({ sort: e.target.value as Filters["sort"] })}
          >
            {SORTS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
          <button className="btn btn-ghost lg:hidden" onClick={() => setPanelOpen((v) => !v)}>
            Фильтры{activeCount ? ` · ${activeCount}` : ""}
          </button>
        </div>
      </header>

      {fromWizard && (
        <div className="card mt-6 flex flex-wrap items-center justify-between gap-4 border-aurora-300 bg-aurora-50 p-5">
          <p className="text-sm">
            <b className="font-semibold">Подобрано по вашей заявке.</b>{" "}
            <span className="text-ink-2">
              Фильтры ниже уже настроены — их можно ослабить, если результатов мало.
            </span>
          </p>
          <Link href="/onboarding" className="btn btn-ghost !py-2 text-sm">
            Изменить ответы
          </Link>
        </div>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-[280px_1fr]">
        <aside className={`${panelOpen ? "block" : "hidden"} lg:block`}>
          <div className="card sticky top-28 space-y-5 p-5">
            <div>
              <label className="label" htmlFor="q">
                Поиск
              </label>
              <input
                id="q"
                className="field"
                placeholder="Имя, специализация…"
                defaultValue={filters.q}
                onKeyDown={(e) => {
                  if (e.key === "Enter") apply({ q: (e.target as HTMLInputElement).value });
                }}
                onBlur={(e) => e.target.value !== filters.q && apply({ q: e.target.value })}
              />
            </div>

            <div>
              <label className="label" htmlFor="category">
                Направление
              </label>
              <select
                id="category"
                className="field"
                value={filters.category}
                onChange={(e) => apply({ category: e.target.value })}
              >
                <option value="">Любое</option>
                {CATEGORIES.filter((c) => c.mapsTo === "category").map((c) => (
                  <optgroup key={c.id} label={c.label}>
                    {c.subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            <div>
              <label className="label" htmlFor="language">
                Язык обучения
              </label>
              <select
                id="language"
                className="field"
                value={filters.language}
                onChange={(e) =>
                  apply({ language: e.target.value, native_speaker: e.target.value ? filters.native_speaker : false })
                }
              >
                <option value="">Любой</option>
                {LANGUAGE_CATEGORY.subjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="label" htmlFor="price">
                Цена за урок, до
              </label>
              <select
                id="price"
                className="field"
                value={filters.max_price_cents}
                onChange={(e) => apply({ max_price_cents: e.target.value })}
              >
                <option value="">Без ограничений</option>
                {[50000, 100000, 200000, 400000].map((cents) => (
                  <option key={cents} value={cents}>
                    {money(cents, DEFAULT_CURRENCY)}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label" htmlFor="rating">
                  Рейтинг
                </label>
                <select
                  id="rating"
                  className="field"
                  value={filters.min_rating}
                  onChange={(e) => apply({ min_rating: e.target.value })}
                >
                  <option value="">Любой</option>
                  <option value="4">от 4.0</option>
                  <option value="4.5">от 4.5</option>
                  <option value="4.8">от 4.8</option>
                </select>
              </div>
              <div>
                <label className="label" htmlFor="experience">
                  Опыт
                </label>
                <select
                  id="experience"
                  className="field"
                  value={filters.min_experience}
                  onChange={(e) => apply({ min_experience: e.target.value })}
                >
                  <option value="">Любой</option>
                  <option value="1">от 1 года</option>
                  <option value="3">от 3 лет</option>
                  <option value="5">от 5 лет</option>
                  <option value="10">от 10 лет</option>
                </select>
              </div>
            </div>

            <fieldset className="space-y-2.5">
              <legend className="label">Дополнительно</legend>
              {[
                { key: "native_speaker" as const, label: "Носитель языка", disabled: !filters.language },
                { key: "has_trial" as const, label: "Есть пробный урок", disabled: false },
                { key: "verified_only" as const, label: "Проверенный профиль", disabled: false },
              ].map((item) => (
                <label
                  key={item.key}
                  className={`flex items-center gap-2.5 text-sm ${item.disabled ? "opacity-40" : "cursor-pointer"}`}
                  title={item.disabled ? "Сначала выберите язык обучения" : undefined}
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-[var(--color-aurora-600)]"
                    checked={filters[item.key]}
                    disabled={item.disabled}
                    onChange={(e) => apply({ [item.key]: e.target.checked } as Partial<Filters>)}
                  />
                  {item.label}
                </label>
              ))}
            </fieldset>

            {activeCount > 0 && (
              <button className="btn btn-ghost w-full" onClick={() => router.replace("/tutors")}>
                Сбросить фильтры
              </button>
            )}
          </div>
        </aside>

        <section>
          {error && (
            <div className="card border-coral-500/40 bg-coral-100 p-5 text-sm">
              <b className="font-semibold">Не получилось загрузить каталог.</b> {error}
              <button className="btn btn-ghost mt-4 !py-2" onClick={() => void load(0)}>
                Повторить
              </button>
            </div>
          )}

          {loading && page === 0 ? (
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <TutorCardSkeleton key={i} />
              ))}
            </div>
          ) : tutors.length > 0 ? (
            <>
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {tutors.map((tutor) => (
                  <TutorCard key={tutor.user_id} tutor={tutor} />
                ))}
              </div>
              {!exhausted && (
                <div className="mt-8 flex justify-center">
                  <button
                    className="btn btn-ghost"
                    disabled={loading}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    {loading ? "Загружаем…" : "Показать ещё"}
                  </button>
                </div>
              )}
            </>
          ) : (
            !error && <EmptyState hasFilters={activeCount > 0} category={filters.category} />
          )}
        </section>
      </div>
    </div>
  );
}

function EmptyState({ hasFilters, category }: { hasFilters: boolean; category: string }) {
  const subject = CATEGORIES.flatMap((c) => c.subjects).find((s) => s.id === category);
  return (
    <div className="card flex flex-col items-center gap-3 p-14 text-center">
      <span className="text-3xl" aria-hidden>
        🔍
      </span>
      <p className="display text-xl">
        {subject ? `Пока нет репетиторов: ${subject.label.toLowerCase()}` : "Ничего не нашлось"}
      </p>
      <p className="max-w-md text-sm text-ink-3">
        {hasFilters
          ? "Попробуйте ослабить фильтры — например, убрать ограничение по цене или рейтингу."
          : "Каталог наполняется. Пройдите подбор, чтобы мы знали, кого вам показать."}
      </p>
      <Link href="/onboarding" className="btn btn-primary mt-2">
        Пройти подбор
      </Link>
    </div>
  );
}
