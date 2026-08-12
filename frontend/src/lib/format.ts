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

/** Russian plural forms follow a 1/few/many split, not singular/plural — `n`
 * years is "год" (1), "года" (2-4), or "лет" (0, 5+, and the 11-14 teens). */
export function pluralRu(n: number, [one, few, many]: [string, string, string]): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}
