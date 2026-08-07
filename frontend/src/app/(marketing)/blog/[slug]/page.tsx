import Link from "next/link";
import { notFound } from "next/navigation";

import { fetchPublic } from "@/lib/server-api";
import type { Article } from "@/lib/types";

type Params = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Params) {
  const { slug } = await params;
  const article = await fetchPublic<Article | null>(`/cms/articles/${slug}`, null);
  return {
    title: article?.seo_title || article?.title || "Статья",
    description: article?.seo_description ?? undefined,
  };
}

export default async function ArticlePage({ params }: Params) {
  const { slug } = await params;
  const article = await fetchPublic<Article | null>(`/cms/articles/${slug}`, null);
  if (!article) notFound();

  return (
    <div className="mx-auto max-w-2xl px-5 py-10">
      <nav className="mb-6 text-sm text-ink-3">
        <Link href="/blog" className="hover:text-ink">
          Блог
        </Link>
        <span className="mx-2">/</span>
        <span>{article.title}</span>
      </nav>

      <article>
        <h1 className="display text-[clamp(1.8rem,3.5vw,2.6rem)]">{article.title}</h1>
        <p className="mt-2 text-sm text-ink-3">
          {new Date(article.created_at).toLocaleDateString("ru-RU")}
        </p>
        <div className="mt-8 whitespace-pre-line leading-relaxed text-ink-2">{article.body}</div>
      </article>
    </div>
  );
}
