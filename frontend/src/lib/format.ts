/** Prices travel as integer minor units + an ISO currency code. */

export const DEFAULT_CURRENCY = process.env.NEXT_PUBLIC_CURRENCY ?? "USD";

export function money(cents: number, currency = DEFAULT_CURRENCY): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency,
    maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100);
}

export function initials(name: string | null | undefined, fallback = "EB"): string {
  if (!name) return fallback;
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || fallback;
}
