import Link from "next/link";

import { ArcDivider } from "@/components/brand";

export default function HomePage() {
  return (
    <>
      <Hero />
      <Features />
      <HowItWorks />
      <Voices />
      <Faq />
      <FinalCta />
    </>
  );
}

/* ------------------------------- Hero ---------------------------------- */

function Hero() {
  return (
    <section className="border-b border-line">
      <div className="mx-auto max-w-7xl px-5 pb-14 pt-14 md:pb-20 md:pt-20">
        <div className="mx-auto max-w-2xl animate-rise text-center">
          <span className="chip mx-auto">
            <span className="h-1.5 w-1.5 rounded-full bg-jade-500" />
            Личный кабинет для занятий один на один
          </span>

          <h1 className="display mt-5 text-[clamp(2.6rem,6.5vw,4.6rem)]">
            Учитесь <span className="arc-underline">с наставником</span>, не в одиночку
          </h1>

          <p className="mt-6 text-lg leading-relaxed text-ink-2">
            Личные сообщения с преподавателем, AI-помощник для домашних заданий и объяснений тем,
            учебные материалы и поддержка — всё в одном личном кабинете.
          </p>

          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Link href="/login" className="btn btn-primary">
              Войти в кабинет
            </Link>
            <Link href="/blog" className="btn btn-ghost">
              Читать блог
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------ Features -------------------------------- */

const FEATURES = [
  {
    title: "Сообщения с преподавателем",
    text: "Личный чат с вложениями — обсуждайте задания и вопросы напрямую, без звонков и почты.",
    accent: "bg-aurora-100 text-aurora-700",
    emoji: "💬",
  },
  {
    title: "AI-помощник",
    text: "Генерация домашних заданий, объяснение тем и разбор урока — доступно прямо в кабинете.",
    accent: "bg-citrus-100 text-citrus-700",
    emoji: "✨",
  },
  {
    title: "Учебные материалы",
    text: "Статьи и гайды в блоге платформы, доступные на нескольких языках.",
    accent: "bg-jade-100 text-jade-700",
    emoji: "📚",
  },
  {
    title: "Поддержка",
    text: "Открывайте обращение прямо из кабинета — команда поддержки отвечает в том же чате.",
    accent: "bg-aurora-100 text-aurora-700",
    emoji: "🛟",
  },
];

function Features() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-16" id="features">
      <SectionHead
        eyebrow="Что внутри"
        title="Всё нужное для занятий — в одном месте"
      />
      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {FEATURES.map((f) => (
          <div key={f.title} className="card p-6">
            <span
              className={`${f.accent} flex h-12 w-12 items-center justify-center rounded-2xl text-xl`}
              aria-hidden
            >
              {f.emoji}
            </span>
            <h3 className="display mt-4 text-lg">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-3">{f.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ---------------------------- How it works ----------------------------- */

const STEPS = [
  {
    title: "Получите доступ",
    text: "Аккаунт создаёт администратор площадки — вы получаете email и пароль для входа.",
    accent: "bg-aurora-100 text-aurora-700",
  },
  {
    title: "Заходите в кабинет",
    text: "Сообщения, AI-помощник и уведомления — всё сразу после входа, без лишних настроек.",
    accent: "bg-citrus-100 text-citrus-700",
  },
  {
    title: "Занимайтесь и общайтесь",
    text: "Пишите преподавателю, пользуйтесь AI-инструментами и обращайтесь в поддержку при необходимости.",
    accent: "bg-jade-100 text-jade-700",
  },
];

function HowItWorks() {
  return (
    <section id="how" className="bg-paper-2 py-16">
      <div className="mx-auto max-w-7xl px-5">
        <SectionHead eyebrow="Как это работает" title="Три шага — и вы в кабинете" />

        <ol className="mt-10 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step.title} className="relative">
              <span
                className={`${step.accent} display flex h-12 w-12 items-center justify-center rounded-2xl text-xl`}
              >
                {index + 1}
              </span>
              <h3 className="display mt-4 text-xl">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-3">{step.text}</p>
              {index < STEPS.length - 1 && (
                <span
                  aria-hidden
                  className="absolute -right-3 top-6 hidden h-px w-6 border-t-2 border-dashed border-line md:block"
                />
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ------------------------------- Voices -------------------------------- */

const VOICES = [
  {
    quote: "Вопросы к преподавателю больше не теряются в почте — всё в одном чате.",
    name: "Айпери",
    role: "студентка",
  },
  {
    quote: "AI-помощник разбирает тему за пару минут, когда преподаватель не на связи.",
    name: "Эрлан",
    role: "родитель",
  },
  {
    quote: "Обращения в поддержку решаются быстрее, чем по почте.",
    name: "Мария",
    role: "преподаватель",
  },
];

function Voices() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-16">
      <SectionHead eyebrow="Отзывы" title="Что говорят" />
      <div className="mt-10 grid gap-5 md:grid-cols-3">
        {VOICES.map((voice) => (
          <figure key={voice.name} className="card flex flex-col gap-5 p-6">
            <span className="display text-4xl leading-none text-aurora-300" aria-hidden>
              &ldquo;
            </span>
            <blockquote className="flex-1 leading-relaxed text-ink-2">{voice.quote}</blockquote>
            <figcaption className="border-t border-line pt-4 text-sm">
              <span className="font-semibold">{voice.name}</span>
              <span className="text-ink-3"> · {voice.role}</span>
            </figcaption>
          </figure>
        ))}
      </div>
      <ArcDivider />
    </section>
  );
}

/* -------------------------------- FAQ ---------------------------------- */

const FAQ = [
  [
    "Как получить доступ?",
    "Регистрация в один клик недоступна — аккаунт создаёт администратор площадки и выдаёт данные для входа.",
  ],
  [
    "С кем я буду переписываться?",
    "С преподавателем или наставником, к которому вас прикрепил администратор — чат доступен сразу в кабинете.",
  ],
  [
    "Что умеет AI-помощник?",
    "Генерирует задания по теме, объясняет материал и разбирает конспект урока — доступен в разделе «AI-помощник».",
  ],
  [
    "Что делать, если возник вопрос по работе платформы?",
    "Откройте обращение в разделе поддержки в кабинете — команда ответит в том же чате.",
  ],
];

function Faq() {
  return (
    <section className="mx-auto max-w-3xl px-5 py-16">
      <SectionHead eyebrow="Вопросы" title="Коротко о главном" center />
      <div className="mt-10 space-y-3">
        {FAQ.map(([question, answer]) => (
          <details key={question} className="card group p-5 [&_summary::-webkit-details-marker]:hidden">
            <summary className="flex cursor-pointer items-center justify-between gap-4 font-semibold">
              {question}
              <span className="text-ink-3 transition-transform group-open:rotate-45" aria-hidden>
                <svg width="18" height="18" viewBox="0 0 18 18">
                  <path d="M9 3v12M3 9h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </span>
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-ink-3">{answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------ Final CTA ------------------------------ */

function FinalCta() {
  return (
    <section className="mx-auto max-w-7xl px-5 pb-8">
      <div className="card flex flex-col items-center gap-6 bg-aurora-50 p-12 text-center">
        <h2 className="display max-w-2xl text-[clamp(1.9rem,4vw,2.8rem)]">
          Данные для входа уже есть?
        </h2>
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/login" className="btn btn-primary">
            Войти в кабинет
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------- Shared -------------------------------- */

function SectionHead({
  eyebrow,
  title,
  text,
  center = false,
}: {
  eyebrow: string;
  title: string;
  text?: string;
  center?: boolean;
}) {
  return (
    <div className={center ? "text-center" : ""}>
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">{eyebrow}</p>
      <h2 className="display mt-3 text-[clamp(1.9rem,4vw,2.8rem)]">{title}</h2>
      {text && (
        <p className={`mt-4 max-w-2xl leading-relaxed text-ink-3 ${center ? "mx-auto" : ""}`}>
          {text}
        </p>
      )}
    </div>
  );
}
