import Link from "next/link";

import { Logo } from "@/components/brand";

const COLUMNS = [
  {
    title: "Кабинет",
    links: [
      { href: "/dashboard", label: "Личный кабинет" },
      { href: "/login", label: "Вход" },
    ],
  },
  {
    title: "Платформа",
    links: [
      { href: "/#features", label: "Что внутри" },
      { href: "/#how", label: "Как это работает" },
      { href: "/blog", label: "Блог" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-line bg-paper-2">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 md:grid-cols-3">
        <div className="md:col-span-1">
          <Logo />
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-ink-3">
            Личный кабинет для занятий с наставником: сообщения, AI-помощник и учебные материалы в
            одном месте.
          </p>
        </div>

        {COLUMNS.map((col) => (
          <div key={col.title}>
            <h3 className="mb-3 text-sm font-semibold">{col.title}</h3>
            <ul className="space-y-2">
              {col.links.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-ink-3 transition-colors hover:text-aurora-700"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="border-t border-line">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-5 py-6 text-xs text-ink-3 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} EduBridge. Бишкек, Кыргызстан.</p>
          <div className="flex gap-4">
            <Link href="/privacy" className="hover:text-aurora-700">
              Конфиденциальность
            </Link>
            <Link href="/terms" className="hover:text-aurora-700">
              Условия использования
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
