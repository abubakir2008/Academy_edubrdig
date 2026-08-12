"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";

import { Logo } from "@/components/brand";
import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";

const NAV = [
  { href: "/#features", label: "Что внутри" },
  { href: "/#how", label: "Как это работает" },
  { href: "/tutors", label: "Репетиторы" },
  { href: "/blog", label: "Блог" },
];

export function SiteHeader() {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => setOpen(false), [pathname]);

  return (
    <header
      className={`sticky top-0 z-50 transition-colors ${
        scrolled ? "border-b border-line bg-paper/85 backdrop-blur-md" : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-18 max-w-7xl items-center gap-6 px-5 py-3.5">
        <Logo />

        <nav className="hidden items-center gap-1 lg:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-full px-3.5 py-2 text-sm font-medium text-ink-2 transition-colors hover:bg-aurora-50 hover:text-aurora-700"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {!loading && user ? (
            <>
              <Link href="/dashboard" className="hidden items-center gap-2 sm:flex">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-aurora-600 text-sm font-semibold text-white">
                  {initials(user.full_name ?? user.email)}
                </span>
                <span className="text-sm font-medium">Кабинет</span>
              </Link>
              <button onClick={() => void logout()} className="btn btn-ghost !px-4 !py-2 text-sm">
                Выйти
              </button>
            </>
          ) : (
            <Link href="/login" className="btn btn-primary !px-5 !py-2.5 text-sm">
              Войти
            </Link>
          )}
          <button
            className="btn btn-ghost !px-3 !py-2 lg:hidden"
            onClick={() => setOpen((v) => !v)}
            aria-label="Меню"
            aria-expanded={open}
          >
            {open ? <X className="h-4.5 w-4.5" aria-hidden /> : <Menu className="h-4.5 w-4.5" aria-hidden />}
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-line bg-paper-2 px-5 py-4 lg:hidden">
          <nav className="flex flex-col gap-1">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-xl px-3 py-2.5 text-sm font-medium text-ink-2 hover:bg-aurora-50"
              >
                {item.label}
              </Link>
            ))}
            {!user && (
              <Link href="/login" className="rounded-xl px-3 py-2.5 text-sm font-medium text-ink-2 hover:bg-aurora-50">
                Войти
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
