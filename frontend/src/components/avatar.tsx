"use client";

import { useState } from "react";

import { initials } from "@/lib/format";

const SIZES = {
  sm: "h-8 w-8 text-[11px]",
  md: "h-9 w-9 text-xs",
  lg: "h-12 w-12 text-sm",
  xl: "h-28 w-28 text-3xl",
} as const;

/**
 * A person's photo, or an initials badge when there isn't one (or the photo
 * fails to load) — the same "circle with a fallback" shown across the site
 * (header, sidebar, tutor cards/profile, course rosters). One implementation
 * so the fallback logic can't drift between call sites.
 */
export function Avatar({
  name,
  url,
  size = "md",
  className = "",
}: {
  name: string | null | undefined;
  url?: string | null;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const [broken, setBroken] = useState(false);
  const dims = SIZES[size];

  if (url && !broken) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={name ?? ""}
        className={`shrink-0 rounded-full border border-line object-cover ${dims} ${className}`}
        onError={() => setBroken(true)}
      />
    );
  }
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full bg-aurora-100 font-semibold text-aurora-700 ${dims} ${className}`}
    >
      {initials(name)}
    </span>
  );
}
