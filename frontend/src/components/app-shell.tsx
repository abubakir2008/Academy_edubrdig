"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  BookOpen,
  Bell,
  ClipboardList,
  GraduationCap,
  Home,
  Inbox,
  LifeBuoy,
  MessageSquare,
  Settings,
  Shield,
  Users,
  type LucideIcon,
} from "lucide-react";

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

type Tab = { href: string; label: string; icon: LucideIcon };

const COURSES_TAB: Tab = { href: "/dashboard/courses", label: "Курсы", icon: BookOpen };

const NOTIFICATIONS_TAB: Tab = { href: "/dashboard/notifications", label: "Уведомления", icon: Bell };
const SUPPORT_TAB: Tab = { href: "/dashboard/support-tickets", label: "Тикеты", icon: LifeBuoy };
const CMS_TAB: Tab = { href: "/dashboard/cms", label: "Контент", icon: BookOpen };
const ADMIN_TAB: Tab = { href: "/dashboard/admin", label: "Админ", icon: Shield };
const USERS_TAB: Tab = { href: "/dashboard/admin/users", label: "Пользователи", icon: Users };
const LESSON_ANALYTICS_TAB: Tab = { href: "/dashboard/admin/lessons", label: "Аналитика", icon: BarChart3 };
const LEADS_TAB: Tab = { href: "/dashboard/leads", label: "Заявки", icon: Inbox };
const MESSAGES_TAB: Tab = { href: "/dashboard/messages", label: "Сообщения", icon: MessageSquare };
const TUTORS_TAB: Tab = { href: "/dashboard/tutors", label: "Репетиторы", icon: GraduationCap };
const HOMEWORK_TAB: Tab = { href: "/dashboard/homework", label: "Задания", icon: ClipboardList };

const OVERVIEW_TAB: Tab = { href: "/dashboard", label: "Обзор", icon: Home };
const SETTINGS_TAB: Tab = { href: "/dashboard/settings", label: "Настройки", icon: Settings };

// A student can browse every tutor on the platform and message one
// directly — a tutor doesn't need to browse their own peers, so this stays
// off TUTOR_TABS below. Homework is student/tutor-only (see calendar's
// homework.py — admin/super_admin get a 403 from /homework/me), so it
// doesn't go on the staff tab set below.
const USER_TABS: Tab[] = [OVERVIEW_TAB, COURSES_TAB, TUTORS_TAB, HOMEWORK_TAB, MESSAGES_TAB, SETTINGS_TAB];
const TUTOR_TABS: Tab[] = [OVERVIEW_TAB, COURSES_TAB, HOMEWORK_TAB, MESSAGES_TAB, SETTINGS_TAB];

/** admin/super_admin see every staff tab; moderator (and anyone else without
 * a dedicated tab set) just gets the generic overview + settings. */
function tabsFor(role: string | undefined): Tab[] {
  const base = (() => {
    if (role === "tutor") return TUTOR_TABS;
    if (role === "student") return USER_TABS;

    if (role === "admin" || role === "super_admin") {
      return [ADMIN_TAB, USERS_TAB, LESSON_ANALYTICS_TAB, LEADS_TAB, COURSES_TAB, SUPPORT_TAB, CMS_TAB, SETTINGS_TAB];
    }
    return [OVERVIEW_TAB, SETTINGS_TAB];
  })();
  // Every role gets the same inbox, inserted right before "Настройки".
  const settingsIndex = base.findIndex((t) => t.href === "/dashboard/settings");
  const withNotifications = [...base];
  withNotifications.splice(settingsIndex === -1 ? base.length : settingsIndex, 0, NOTIFICATIONS_TAB);
  return withNotifications;
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
                    ? "bg-aurora-600 text-white shadow-glow"
                    : "text-ink-2 hover:bg-aurora-50 hover:text-aurora-700"
                }`}
              >
                <tab.icon className="h-4.5 w-4.5 shrink-0" strokeWidth={1.9} aria-hidden />
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

        {/* min-w-0 overrides the flex item's default min-width:auto — without
        it, any wide descendant (the weekly calendar's overflow-x-auto grid,
        a wide table) stretches this whole column instead of scrolling
        inside its own box, and the entire page gains horizontal overflow. */}
        <div className="min-h-screen min-w-0 flex-1 pb-20 lg:pb-0">
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
              <tab.icon className="h-4.5 w-4.5" strokeWidth={1.9} aria-hidden />
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
