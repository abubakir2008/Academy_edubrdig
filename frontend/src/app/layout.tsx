import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { AuthProvider } from "@/lib/auth";

import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "EduBridge — личный кабинет для занятий на курсе",
    template: "%s · EduBridge",
  },
  description:
    "Сообщения с преподавателем, расписание занятий с Zoom и AI-помощник — всё в одном личном кабинете для курса.",
  openGraph: {
    title: "EduBridge — личный кабинет для занятий на курсе",
    description: "Сообщения с преподавателем, расписание занятий с Zoom и AI-помощник в одном кабинете.",
    type: "website",
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
