import { countWord } from "@/lib/format";

export function Stars({ value, size = 14 }: { value: number; size?: number }) {
  const rounded = Math.round(value * 2) / 2;
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`Рейтинг ${value} из 5`}>
      {[1, 2, 3, 4, 5].map((i) => {
        const fill = rounded >= i ? 1 : rounded >= i - 0.5 ? 0.5 : 0;
        return (
          <svg key={i} width={size} height={size} viewBox="0 0 20 20" aria-hidden>
            <defs>
              <linearGradient id={`half-${i}-${size}`}>
                <stop offset="50%" stopColor="var(--color-citrus-500)" />
                <stop offset="50%" stopColor="var(--color-line)" />
              </linearGradient>
            </defs>
            <path
              d="M10 1.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L1.6 7.7l5.8-.8L10 1.6z"
              fill={
                fill === 1
                  ? "var(--color-citrus-500)"
                  : fill === 0.5
                    ? `url(#half-${i}-${size})`
                    : "var(--color-line)"
              }
            />
          </svg>
        );
      })}
    </span>
  );
}

export function RatingLine({ rating, reviews }: { rating: number; reviews: number }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <Stars value={rating} />
      <span className="font-semibold">{rating ? rating.toFixed(1) : "—"}</span>
      <span className="text-ink-3">{countWord(reviews, "review")}</span>
    </div>
  );
}
