import Link from "next/link";

import { Logo } from "@/components/brand";
import { CATEGORIES } from "@/lib/catalog";

const COLUMNS = [
  {
    title: "Ученикам",
    links: [
      { href: "/onboarding", label: "Подобрать репетитора" },
      { href: "/tutors", label: "Каталог" },
      { href: "/dashboard", label: "Личный кабинет" },
    ],
  },
  {
    title: "Репетиторам",
    links: [
      { href: "/#tutor", label: "Как мы платим" },
      { href: "/#how", label: "Правила площадки" },
      { href: "/blog", label: "Блог" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-line bg-paper-2">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 md:grid-cols-4">
        <div className="md:col-span-1">
          <Logo />
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-ink-3">
            Площадка живых занятий: подбираем репетитора под вашу цель, а не под первую строчку
            выдачи.
          </p>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold">Направления</h3>
          <ul className="space-y-2">
            {CATEGORIES.slice(0, 5).map((c) => (
              <li key={c.id}>
                <Link
                  href={`/tutors?category=${c.id}`}
                  className="text-sm text-ink-3 transition-colors hover:text-aurora-700"
                >
                  {c.label}
                </Link>
              </li>
            ))}
          </ul>
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
          <p>Оплата картами и локальными кошельками · Возврат по правилам площадки</p>
        </div>
      </div>
    </footer>
  );
}
