import type { ReactNode } from "react";

/** Shared split layout for /login and /register. */
export function AuthShell({
  title,
  subtitle,
  children,
  aside,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  aside: ReactNode;
}) {
  return (
    <div className="mx-auto grid max-w-6xl gap-12 px-5 py-12 lg:grid-cols-2 lg:py-20">
      <div className="mx-auto w-full max-w-md">
        <h1 className="display text-[clamp(2rem,4vw,2.8rem)]">{title}</h1>
        <p className="mt-3 text-ink-3">{subtitle}</p>
        <div className="mt-8">{children}</div>
      </div>

      <div className="card grain relative hidden overflow-hidden bg-ink p-10 text-paper lg:block">
        <div
          aria-hidden
          className="absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-aurora-600/40 blur-3xl"
        />
        <div className="relative">{aside}</div>
      </div>
    </div>
  );
}

export function AsideList({ title, items }: { title: string; items: string[] }) {
  return (
    <>
      <h2 className="display text-3xl text-paper-2">{title}</h2>
      <ul className="mt-8 space-y-5">
        {items.map((item) => (
          <li key={item} className="flex gap-3 text-paper/75">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-citrus-500" aria-hidden />
            <span className="leading-relaxed">{item}</span>
          </li>
        ))}
      </ul>
    </>
  );
}
