import Link from "next/link";

export function HeroPicker() {
  return (
    <div className="card flex w-full max-w-md flex-col items-center gap-5 p-8 text-center shadow-lift sm:p-10">
      <p className="text-ink-2">
        Пара вопросов о цели, уровне и бюджете — и мы покажем подходящих репетиторов.
      </p>

      <Link href="/onboarding" className="btn btn-primary w-full !py-3.5 text-base">
        Подобрать репетитора
        <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden>
          <path
            d="M4 10h12m0 0l-5-5m5 5l-5 5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </Link>

      <p className="text-xs text-ink-3">Это 2 минуты, бесплатно</p>
    </div>
  );
}
