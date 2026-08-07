import Link from "next/link";

/**
 * The mark is the product name made literal: two piers and an arc between them.
 * It reappears as `ArcDivider` between sections, so the whole site reads as one
 * continuous bridge.
 */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link href="/" className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg
        viewBox="0 0 40 32"
        className="h-8 w-10 shrink-0"
        aria-hidden
        fill="none"
        strokeLinecap="round"
      >
        <path
          d="M3 25c0-11 7.6-18 17-18s17 7 17 18"
          stroke="var(--color-aurora-600)"
          strokeWidth="3.2"
        />
        <path d="M3 25h34" stroke="var(--color-ink)" strokeWidth="3.2" />
        <path d="M12 25V15M20 25V10M28 25v-10" stroke="var(--color-citrus-500)" strokeWidth="2.4" />
      </svg>
      <span className="display text-xl tracking-tight">
        Edu<span className="text-aurora-600">Bridge</span>
      </span>
    </Link>
  );
}

export function ArcDivider({ flip = false }: { flip?: boolean }) {
  return (
    <div className="pointer-events-none select-none" aria-hidden>
      <svg
        viewBox="0 0 1440 60"
        preserveAspectRatio="none"
        className={`h-10 w-full text-line ${flip ? "rotate-180" : ""}`}
      >
        <path
          d="M0 58C240 58 360 6 720 6s480 52 720 52"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeDasharray="10 12"
        />
      </svg>
    </div>
  );
}
