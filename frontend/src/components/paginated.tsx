"use client";

import { useState, type ReactNode } from "react";

const PAGE_SIZE = 6;

/** Grids items up and paginates them client-side — keeps long lists (many
 * categories, leads, users, log entries) from turning into one giant
 * unreadable column. */
export function Paginated<T>({
  items,
  renderItem,
  empty,
  pageSize = PAGE_SIZE,
}: {
  items: T[];
  renderItem: (item: T) => ReactNode;
  empty: string;
  pageSize?: number;
}) {
  const [page, setPage] = useState(0);

  if (!items.length) return <p className="card mt-4 p-6 text-sm text-ink-3">{empty}</p>;

  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const current = Math.min(page, totalPages - 1);
  const pageItems = items.slice(current * pageSize, current * pageSize + pageSize);

  return (
    <>
      <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{pageItems.map(renderItem)}</ul>
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-4">
          <button
            className="btn btn-ghost !py-1.5 text-xs"
            disabled={current === 0}
            onClick={() => setPage(current - 1)}
          >
            ← Назад
          </button>
          <span className="text-xs text-ink-3">
            Стр. {current + 1} из {totalPages} · {items.length} всего
          </span>
          <button
            className="btn btn-ghost !py-1.5 text-xs"
            disabled={current === totalPages - 1}
            onClick={() => setPage(current + 1)}
          >
            Дальше →
          </button>
        </div>
      )}
    </>
  );
}
