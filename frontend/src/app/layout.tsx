import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { AuthProvider } from "@/lib/auth";

import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

const SITE_URL = "https://academy.edubridge.bond";
const DEFAULT_TITLE = "EduBridge — личный кабинет для занятий на курсе";
const DEFAULT_DESCRIPTION =
  "Сообщения с преподавателем, расписание занятий с Zoom и AI-помощник — всё в одном личном кабинете для курса.";

export const metadata: Metadata = {
  // Resolves every relative URL in openGraph/twitter metadata (including
  // the auto-detected icon.png / opengraph-image.png below) to an absolute
  // one — without this, social previews and search results can end up
  // pointing at broken relative paths.
  metadataBase: new URL(SITE_URL),
  title: {
    default: DEFAULT_TITLE,
    template: "%s · EduBridge",
  },
  description: DEFAULT_DESCRIPTION,
  alternates: { canonical: "/" },
  robots: { index: true, follow: true },
  openGraph: {
    title: DEFAULT_TITLE,
    description: "Сообщения с преподавателем, расписание занятий с Zoom и AI-помощник в одном кабинете.",
    type: "website",
    url: SITE_URL,
    siteName: "EduBridge",
    locale: "ru_RU",
  },
  twitter: {
    card: "summary_large_image",
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
  },
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
};

// Marketing pages render <SiteHeader>/<SiteFooter> via (marketing)/layout.tsx;
// the app shell (dashboard) renders its own top bar + tab nav via
// (app)/layout.tsx — neither belongs here, so a logged-in user inside the
// dashboard never sees the public marketing chrome around their own tools.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={inter.variable}>
      <body className="min-h-screen antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
