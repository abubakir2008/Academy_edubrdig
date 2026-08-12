import type { MetadataRoute } from "next";

import { fetchPublic } from "@/lib/server-api";
import type { Article } from "@/lib/types";

const SITE_URL = "https://academy.edubridge.bond";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/blog`, changeFrequency: "daily", priority: 0.7 },
    { url: `${SITE_URL}/support`, changeFrequency: "monthly", priority: 0.3 },
    { url: `${SITE_URL}/privacy`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/terms`, changeFrequency: "yearly", priority: 0.2 },
  ];

  const articles = await fetchPublic<Article[]>("/cms/articles?type=blog&limit=200", []);
  const articleRoutes: MetadataRoute.Sitemap = articles
    .filter((a) => a.published)
    .map((a) => ({
      url: `${SITE_URL}/blog/${a.slug}`,
      lastModified: a.updated_at,
      changeFrequency: "monthly",
      priority: 0.6,
    }));

  return [...staticRoutes, ...articleRoutes];
}
