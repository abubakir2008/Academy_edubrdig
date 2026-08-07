import type { Metadata, Viewport } from "next";
import { Fraunces, Inter } from "next/font/google";

import { AuthProvider } from "@/lib/auth";

import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

// Editorial serif for display type — the main visual break from the usual
// all-sans marketplace look.
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
  axes: ["SOFT", "WONK", "opsz"],
});

export const metadata: Metadata = {
  title: {
    default: "EduBridge — репетиторы онлайн под вашу цель",
    template: "%s · EduBridge",
  },
  description:
    "Пройдите короткий подбор — расскажите, что, зачем и как хотите учить, и получите репетиторов, которые подходят именно вам.",
  openGraph: {
    title: "EduBridge — репетиторы онлайн под вашу цель",
    description: "Подбор репетитора за 2 минуты: язык, цель, уровень, ритм и бюджет.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#f8f5ef",
};

// Marketing pages render <SiteHeader>/<SiteFooter> via (marketing)/layout.tsx;
// the app shell (dashboard) renders its own top bar + tab nav via
// (app)/layout.tsx — neither belongs here, so a logged-in user inside the
// dashboard never sees the public marketing chrome around their own tools.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={`${inter.variable} ${fraunces.variable}`}>
      <body className="min-h-screen antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
