"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Logo } from "@/components/brand";
import { API_BASE, get, tokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";

type PushNotification = { id: string; type: string; title: string; body: string | null };

/** Live notifications, for as long as any dashboard page is mounted — a
 * background browser Notification when the tab is hidden and permission was
 * granted (see settings/page.tsx), plus a running unread count fed by the
 * same socket so the nav badge updates without polling. */
function useLiveNotifications(enabled: boolean): number {
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    get<{ unread: number }>("/notifications/me/unread-count", true)
      .then((r) => setUnread(r.unread))
      .catch(() => undefined);
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    const token = tokens.access();
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}${API_BASE}/notifications/ws?token=${token}`);
    ws.onmessage = (event) => {
      const n = JSON.parse(event.data) as PushNotification;
      setUnread((count) => count + 1);
      if (document.hidden && typeof Notification !== "undefined" && Notification.permission === "granted") {
        new Notification(n.title, { body: n.body ?? undefined });
      }
    };
    return () => ws.close();
  }, [enabled]);

  return unread;
}

type Tab = { href: string; label: string; icon: string };

const STUDENT_TABS: Tab[] = [
  { href: "/dashboard", label: "Обзор", icon: "home" },
  { href: "/dashboard/bookings", label: "Бронирования", icon: "calendar" },
  { href: "/dashboard/payments", label: "Оплата", icon: "card" },
  { href: "/dashboard/messages", label: "Сообщения", icon: "chat" },
  { href: "/dashboard/ai", label: "AI-помощник", icon: "spark" },
  { href: "/dashboard/settings", label: "Настройки", icon: "gear" },
];

const TUTOR_TABS: Tab[] = [
  { href: "/dashboard", label: "Обзор", icon: "home" },
  { href: "/dashboard/profile", label: "Профиль", icon: "user" },
  { href: "/dashboard/bookings", label: "Бронирования", icon: "calendar" },
  { href: "/dashboard/wallet", label: "Кошелёк", icon: "card" },
  { href: "/dashboard/messages", label: "Сообщения", icon: "chat" },
  { href: "/dashboard/verification", label: "Верификация", icon: "shield" },
  { href: "/dashboard/ai", label: "AI-помощник", icon: "spark" },
  { href: "/dashboard/settings", label: "Настройки", icon: "gear" },
];

const NOTIFICATIONS_TAB: Tab = { href: "/dashboard/notifications", label: "Уведомления", icon: "bell" };
const MODERATION_TAB: Tab = { href: "/dashboard/moderation", label: "Модерация", icon: "shield" };
const SUPPORT_TAB: Tab = { href: "/dashboard/support-tickets", label: "Тикеты", icon: "chat" };
const PAYOUTS_TAB: Tab = { href: "/dashboard/payouts", label: "Выплаты", icon: "card" };
const CMS_TAB: Tab = { href: "/dashboard/cms", label: "Контент", icon: "gear" };
const ADMIN_TAB: Tab = { href: "/dashboard/admin", label: "Админ", icon: "home" };
const USERS_TAB: Tab = { href: "/dashboard/admin/users", label: "Пользователи", icon: "user" };

const OVERVIEW_TAB: Tab = { href: "/dashboard", label: "Обзор", icon: "home" };
const SETTINGS_TAB: Tab = { href: "/dashboard/settings", label: "Настройки", icon: "gear" };

/** Every staff role sees its own domain tab; admin/super_admin see all of
 * them, matching the backend where require_roles(X, ADMIN, SUPER_ADMIN) gives
 * admins the same access as every specific staff role. */
function tabsFor(role: string | undefined): Tab[] {
  const base = (() => {
    if (role === "tutor") return TUTOR_TABS;
    if (role === "student") return STUDENT_TABS;

    if (role === "admin" || role === "super_admin") {
      return [ADMIN_TAB, USERS_TAB, MODERATION_TAB, SUPPORT_TAB, PAYOUTS_TAB, CMS_TAB, SETTINGS_TAB];
    }
    if (role === "moderator") return [OVERVIEW_TAB, MODERATION_TAB, SETTINGS_TAB];
    if (role === "support_manager") return [OVERVIEW_TAB, SUPPORT_TAB, SETTINGS_TAB];
    if (role === "finance_manager") return [OVERVIEW_TAB, PAYOUTS_TAB, SETTINGS_TAB];
    if (role === "content_manager") return [OVERVIEW_TAB, CMS_TAB, SETTINGS_TAB];
    return [OVERVIEW_TAB, SETTINGS_TAB];
  })();
  // Every role gets the same inbox, inserted right before "Настройки".
  const settingsIndex = base.findIndex((t) => t.href === "/dashboard/settings");
  const withNotifications = [...base];
  withNotifications.splice(settingsIndex === -1 ? base.length : settingsIndex, 0, NOTIFICATIONS_TAB);
  return withNotifications;
}

const ICONS: Record<string, string> = {
  home: "M3 10l7-6 7 6v8a1 1 0 0 1-1 1h-4v-5H8v5H4a1 1 0 0 1-1-1v-8Z",
  calendar: "M4 4h12v13H4V4Zm0 4h12M7 2v4M13 2v4",
  card: "M2 5h16v10H2V5Zm0 4h16M5 12.5h3",
  chat: "M3 4h14v9H7l-4 3V4Z",
  gear: "M10 6.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7ZM3.5 10h1M15.5 10h1M10 3.5v1M10 15.5v1M5.5 5.5l.7.7M13.8 13.8l.7.7M5.5 14.5l.7-.7M13.8 6.2l.7-.7",
  shield: "M10 2l6 2.5v5c0 4-2.5 6.8-6 8.5-3.5-1.7-6-4.5-6-8.5v-5L10 2Z",
  user: "M10 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm-6 8c0-3.3 2.7-6 6-6s6 2.7 6 6",
  bell: "M10 3a4 4 0 0 0-4 4v2.5c0 1-.4 2-1.1 2.7L4 13h12l-.9-.8c-.7-.7-1.1-1.7-1.1-2.7V7a4 4 0 0 0-4-4Zm-1.5 12.5a1.5 1.5 0 0 0 3 0",
  spark: "M10 2.5 12 8l5.5 2-5.5 2-2 5.5-2-5.5L2.5 10 8 8l2-5.5Z",
};

function TabIcon({ name }: { name: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden>
      <path d={ICONS[name] ?? ICONS.home} stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/**
 * Authenticated app shell: replaces the marketing header/footer for
 * everything under /dashboard. A left rail of tabs on desktop, a bottom tab
 * bar on mobile — the same nav model Preply/most SaaS dashboards use, distinct
 * on purpose from the marketing site's top nav so the two contexts never blur.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${pathname}`);
  }, [loading, user, router, pathname]);

  const unread = useLiveNotifications(!loading && !!user);

  if (loading || !user) {
    return <div className="min-h-screen bg-paper" />;
  }

  const tabs = tabsFor(user.role);
  const isActive = (href: string) => (href === "/dashboard" ? pathname === href : pathname.startsWith(href));

  return (
    <div className="min-h-screen bg-paper">
      <div className="mx-auto flex max-w-7xl">
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-paper-2 px-4 py-6 lg:flex">
          <Link href="/" className="px-2">
            <Logo />
          </Link>

          <nav className="mt-8 flex flex-1 flex-col gap-1">
            {tabs.map((tab) => (
              <Link
                key={tab.href}
                href={tab.href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive(tab.href)
                    ? "bg-aurora-600 text-white shadow-lift"
                    : "text-ink-2 hover:bg-aurora-50 hover:text-aurora-700"
                }`}
              >
                <TabIcon name={tab.icon} />
                {tab.label}
                {tab.href === "/dashboard/notifications" && unread > 0 && (
                  <span className="ml-auto rounded-full bg-coral-500 px-1.5 py-0.5 text-[11px] font-semibold text-white">
                    {unread > 99 ? "99+" : unread}
                  </span>
                )}
              </Link>
            ))}
          </nav>

          <div className="mt-auto space-y-3 border-t border-line pt-4">
            <div className="flex items-center gap-2.5 px-2">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-aurora-600 text-sm font-semibold text-white">
                {initials(user.full_name ?? user.email)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{user.full_name || "Без имени"}</p>
                <p className="truncate text-xs text-ink-3">{user.email}</p>
              </div>
            </div>
            <button
              onClick={() => void logout().then(() => router.replace("/"))}
              className="btn btn-ghost w-full !py-2 text-sm"
            >
              Выйти
            </button>
          </div>
        </aside>

        <div className="min-h-screen flex-1 pb-20 lg:pb-0">
          <header className="flex items-center justify-between border-b border-line bg-paper-2/85 px-5 py-3.5 backdrop-blur-md lg:hidden">
            <Link href="/">
              <Logo />
            </Link>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-aurora-600 text-xs font-semibold text-white">
              {initials(user.full_name ?? user.email)}
            </span>
          </header>

          {children}
        </div>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 flex border-t border-line bg-paper-2/95 backdrop-blur-md lg:hidden">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium ${
              isActive(tab.href) ? "text-aurora-700" : "text-ink-3"
            }`}
          >
            <span className="relative">
              <TabIcon name={tab.icon} />
              {tab.href === "/dashboard/notifications" && unread > 0 && (
                <span className="absolute -right-1.5 -top-1 h-2 w-2 rounded-full bg-coral-500" />
              )}
            </span>
            {tab.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
