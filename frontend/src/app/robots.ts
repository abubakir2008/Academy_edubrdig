import type { MetadataRoute } from "next";

const SITE_URL = "https://academy.edubridge.bond";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // The dashboard is behind login and never has content worth
        // indexing; /login and /onboarding are pure forms, not landing
        // content — keeping them out avoids low-value pages competing with
        // the real marketing pages in search results.
        disallow: ["/dashboard", "/login", "/onboarding"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
