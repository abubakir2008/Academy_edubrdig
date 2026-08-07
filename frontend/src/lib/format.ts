/** Prices travel as integer minor units + an ISO currency code. */

export const DEFAULT_CURRENCY = process.env.NEXT_PUBLIC_CURRENCY ?? "USD";

export function money(cents: number, currency = DEFAULT_CURRENCY): string {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency,
    maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
  }).format(cents / 100);
}

const PLURALS: Record<string, [string, string, string]> = {
  lesson: ["урок", "урока", "уроков"],
  review: ["отзыв", "отзыва", "отзывов"],
  year: ["год", "года", "лет"],
  tutor: ["репетитор", "репетитора", "репетиторов"],
};

export function plural(count: number, key: keyof typeof PLURALS | string): string {
  const forms = PLURALS[key] ?? [key, key, key];
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return forms[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return forms[1];
  return forms[2];
}

export const countWord = (count: number, key: string) => `${count} ${plural(count, key)}`;

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
export const weekday = (index: number) => WEEKDAYS[index] ?? "—";

/** "09:00:00" -> "09:00" */
export const clock = (time: string) => time.slice(0, 5);

export function initials(name: string | null | undefined, fallback = "EB"): string {
  if (!name) return fallback;
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || fallback;
}

/** Deterministic accent per tutor so avatars stay stable between renders. */
const AVATAR_TONES = [
  "bg-aurora-100 text-aurora-700",
  "bg-citrus-100 text-citrus-700",
  "bg-jade-100 text-jade-700",
  "bg-coral-100 text-coral-500",
];

export function toneFor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) hash = (hash * 31 + seed.charCodeAt(i)) % 9973;
  return AVATAR_TONES[hash % AVATAR_TONES.length];
}

const FLAGS: Record<string, string> = {
  KG: "🇰🇬", RU: "🇷🇺", KZ: "🇰🇿", US: "🇺🇸", GB: "🇬🇧", TR: "🇹🇷",
  DE: "🇩🇪", FR: "🇫🇷", CN: "🇨🇳", JP: "🇯🇵", KR: "🇰🇷", ES: "🇪🇸",
  IT: "🇮🇹", UZ: "🇺🇿", AE: "🇦🇪", PL: "🇵🇱", UA: "🇺🇦", CA: "🇨🇦",
};

export const flag = (code: string | null | undefined) =>
  (code && FLAGS[code.toUpperCase()]) || "🌍";
