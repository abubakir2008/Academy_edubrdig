import Link from "next/link";

import { fetchPublic } from "@/lib/server-api";
import type { Article } from "@/lib/types";

export const metadata = { title: "Блог — EduBridge" };

export default async function BlogPage() {
  const articles = await fetchPublic<Article[]>("/cms/articles?type=blog&limit=50", []);

  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Блог</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Статьи EduBridge</h1>
      </header>

      <div className="mt-8">
        {articles.length ? (
          <ul className="space-y-3">
            {articles.map((a) => (
              <li key={a.id}>
                <Link href={`/blog/${a.slug}`} className="card block p-5 transition-colors hover:border-aurora-300">
                  <p className="display text-lg">{a.title}</p>
                  <p className="mt-1 text-sm text-ink-3">
                    {new Date(a.created_at).toLocaleDateString("ru-RU")}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="card p-6 text-sm text-ink-3">Статей пока нет.</p>
        )}
      </div>
    </div>
  );
}
