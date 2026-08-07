import Link from "next/link";

import { ArcDivider } from "@/components/brand";
import { HeroPicker } from "@/components/hero-picker";
import { TutorCard } from "@/components/tutor-card";
import { CATEGORIES } from "@/lib/catalog";
import { fetchPublic } from "@/lib/server-api";
import type { TutorSummary } from "@/lib/types";

export default async function HomePage() {
  const [featured, searchStats] = await Promise.all([
    fetchPublic<TutorSummary[]>("/tutors?sort=rating&limit=6", []),
    fetchPublic<{ total: number }>("/search/tutors?limit=1", { total: 0 }),
  ]);

  const avgRating =
    featured.length > 0
      ? featured.reduce((sum, t) => sum + t.rating, 0) / featured.length
      : null;

  return (
    <>
      <Hero tutorCount={searchStats.total} avgRating={avgRating} />
      <Categories />
      <HowItWorks />
      <Featured tutors={featured} />
      <WizardTeaser />
      <Voices />
      <ForTutors />
      <Faq />
      <FinalCta />
    </>
  );
}

/* ------------------------------- Hero ---------------------------------- */

function Hero({ tutorCount, avgRating }: { tutorCount: number; avgRating: number | null }) {
  const stats: [string, string][] = [
    [tutorCount > 0 ? `${tutorCount}+` : "Растёт каждый день", "репетиторов"],
    [String(CATEGORIES.length), "направлений"],
    [avgRating ? avgRating.toFixed(1) : "—", "средний рейтинг"],
    ["0 ₽", "за подбор и заявку"],
  ];

  return (
    <section className="border-b border-line">
      <div className="mx-auto max-w-7xl px-5 pb-14 pt-14 md:pb-20 md:pt-20">
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_1fr]">
          <div className="animate-rise">
            <span className="chip">
              <span className="h-1.5 w-1.5 rounded-full bg-jade-500" />
              Живые занятия один на один
            </span>

            <h1 className="display mt-5 text-[clamp(2.6rem,6.5vw,4.6rem)]">
              Репетитор, который ведёт
              <br className="hidden sm:block" /> к <span className="arc-underline">вашей цели</span>
            </h1>

            <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-2">
              Мы не бросаем вас в каталог из тысячи анкет. Оставьте короткую заявку —{" "}
              <b className="font-semibold text-ink">что</b>, <b className="font-semibold text-ink">зачем</b> и{" "}
              <b className="font-semibold text-ink">как с вами связаться</b> — и мы сами подберём
              репетитора и перезвоним.
            </p>

            <dl className="mt-9 flex flex-wrap gap-x-9 gap-y-4 border-t border-line pt-6">
              {stats.map(([value, label]) => (
                <div key={label}>
                  <dt className="display text-2xl">{value}</dt>
                  <dd className="text-sm text-ink-3">{label}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="flex justify-center lg:justify-end">
            <HeroPicker />
          </div>
        </div>
      </div>
    </section>
  );
}

/* ----------------------------- Categories ------------------------------ */

function Categories() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-16" id="categories">
      <SectionHead
        eyebrow="Направления"
        title="С чего начнём?"
        text="Каждое направление задаёт свои вопросы: языку — уровень A1–C2, школе — класс, экзамену — срок до даты."
      />

      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {CATEGORIES.map((category, index) => (
          <Link
            key={category.id}
            href={`/onboarding?category=${category.id}`}
            className={`card group relative overflow-hidden p-6 transition-all hover:-translate-y-1 hover:border-aurora-300 hover:shadow-lift ${
              index === 0 ? "sm:col-span-2 sm:row-span-1 lg:col-span-2" : ""
            }`}
          >
            <span className="text-3xl" aria-hidden>
              {category.emoji}
            </span>
            <h3 className="display mt-4 text-xl">{category.label}</h3>
            <p className="mt-1.5 text-sm text-ink-3">{category.tagline}</p>
            <p className="mt-4 text-sm font-semibold text-aurora-700 opacity-0 transition-opacity group-hover:opacity-100">
              Пройти подбор →
            </p>
            <span
              aria-hidden
              className="absolute -bottom-10 -right-6 h-24 w-32 rounded-t-full border-t-2 border-dashed border-line transition-colors group-hover:border-aurora-300"
            />
          </Link>
        ))}
      </div>
    </section>
  );
}

/* ---------------------------- How it works ----------------------------- */

const STEPS = [
  {
    title: "Найдите своего репетитора",
    text: "Короткий опрос про предмет, цель, уровень и темп — и мы показываем только тех, кто подходит под этот ответ.",
    accent: "bg-aurora-100 text-aurora-700",
  },
  {
    title: "Начните заниматься",
    text: "Договоритесь о пробном уроке, оплатите на платформе — и учитесь один на один, онлайн.",
    accent: "bg-citrus-100 text-citrus-700",
  },
  {
    title: "Прогрессируйте каждую неделю",
    text: "Расписание, задания и отзывы — в личном кабинете. Не подошло — бесплатно меняем репетитора.",
    accent: "bg-jade-100 text-jade-700",
  },
];

function HowItWorks() {
  return (
    <section id="how" className="bg-paper-2 py-16">
      <div className="mx-auto max-w-7xl px-5">
        <SectionHead eyebrow="Как это работает" title="Три шага — и вы на уроке" />

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

/* ------------------------------ Featured ------------------------------- */

function Featured({ tutors }: { tutors: TutorSummary[] }) {
  return (
    <section className="mx-auto max-w-7xl px-5 py-16">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <SectionHead eyebrow="Репетиторы" title="Кого чаще всего выбирают" />
        <Link href="/tutors" className="btn btn-ghost">
          Открыть каталог
        </Link>
      </div>

      {tutors.length > 0 ? (
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {tutors.map((tutor) => (
            <TutorCard key={tutor.user_id} tutor={tutor} />
          ))}
        </div>
      ) : (
        <div className="card mt-10 flex flex-col items-center gap-3 p-12 text-center">
          <span className="text-3xl" aria-hidden>
            🚧
          </span>
          <p className="display text-xl">Каталог наполняется</p>
          <p className="max-w-md text-sm text-ink-3">
            Анкеты появятся здесь, как только репетиторы пройдут модерацию. Пройдите подбор — и мы
            покажем подходящих сразу, как они появятся.
          </p>
          <Link href="/onboarding" className="btn btn-primary mt-2">
            Пройти подбор
          </Link>
        </div>
      )}
    </section>
  );
}

/* --------------------------- Wizard teaser ----------------------------- */

function WizardTeaser() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-16">
      <div className="card grain relative overflow-hidden bg-ink p-8 text-paper md:p-14">
        <div
          aria-hidden
          className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-aurora-600/40 blur-3xl"
        />
        <div className="relative grid gap-10 lg:grid-cols-2 lg:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-citrus-400">
              Заявка
            </p>
            <h2 className="display mt-3 text-[clamp(2rem,4vw,3rem)] text-paper-2">
              Пара вопросов — и мы сами подберём репетитора
            </h2>
            <p className="mt-5 max-w-lg leading-relaxed text-paper/70">
              Что учите, зачем и как с вами связаться — оставьте заявку, а дальше мы позвоним и
              подберём подходящего репетитора.
            </p>
            <Link href="/onboarding" className="btn btn-accent mt-8">
              Оставить заявку
            </Link>
          </div>

          <div className="space-y-3">
            {[
              { q: "Что вы хотите изучать?", a: "Английский" },
              { q: "Для чего?", a: "IELTS" },
              { q: "Где вы учитесь?", a: "КНУ им. Ж. Баласагына" },
              { q: "Хотите переехать в другую страну?", a: "Германия" },
            ].map((item) => (
              <div
                key={item.q}
                className="rounded-2xl border border-paper/15 bg-paper/5 p-4 backdrop-blur-sm"
              >
                <p className="text-sm text-paper/60">{item.q}</p>
                <p className="mt-1 font-semibold text-paper-2">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------- Voices -------------------------------- */

const VOICES = [
  {
    quote:
      "Раньше выбирала по цене и фото. Здесь меня спросили про дедлайн IELTS — и выдача сразу стала другой.",
    name: "Айпери",
    role: "готовится к IELTS, Бишкек",
  },
  {
    quote:
      "Сыну нужен был не «репетитор по математике», а человек, который вернёт ему интерес. Вопрос про цель это и решил.",
    name: "Эрлан",
    role: "родитель, 7 класс",
  },
  {
    quote:
      "Я репетитор. Заявки приходят с описанием цели и уровня — не трачу первый урок на выяснение.",
    name: "Мария",
    role: "преподаватель английского",
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
              “
            </span>
            <blockquote className="flex-1 leading-relaxed text-ink-2">{voice.quote}</blockquote>
            <figcaption className="border-t border-line pt-4 text-sm">
              <span className="font-semibold">{voice.name}</span>
              <span className="text-ink-3"> · {voice.role}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}

/* ----------------------------- For tutors ------------------------------ */

function ForTutors() {
  return (
    <section id="tutor" className="bg-paper-2 py-16">
      <ArcDivider flip />
      <div className="mx-auto grid max-w-7xl gap-10 px-5 pt-6 lg:grid-cols-2 lg:items-center">
        <div>
          <SectionHead eyebrow="Репетиторам" title="Вы преподаёте — остальное берём на себя" />
          <ul className="mt-8 space-y-4">
            {[
              ["Заявки с контекстом", "Цель, уровень и ритм ученика видны до первого сообщения."],
              ["Расписание и оплата", "Календарь, брони и выплаты на кошелёк — внутри площадки."],
              ["Прозрачный рейтинг", "Отзывы после проведённых уроков, без накруток."],
            ].map(([title, text]) => (
              <li key={title} className="flex gap-3">
                <span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-jade-100 text-jade-700">
                  <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
                    <path d="M2 6.5l2.6 2.6L10 3.5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" />
                  </svg>
                </span>
                <p>
                  <b className="font-semibold">{title}.</b>{" "}
                  <span className="text-ink-3">{text}</span>
                </p>
              </li>
            ))}
          </ul>
          <Link href="/onboarding" className="btn btn-primary mt-8">
            Оставить заявку — мы свяжемся
          </Link>
        </div>

        <div className="card relative overflow-hidden p-8">
          <div className="grid grid-cols-2 gap-4">
            {[
              ["Комиссия", "прозрачная, без скрытых удержаний"],
              ["Выплаты", "на кошелёк площадки"],
              ["Модерация", "проверка документов и сертификатов"],
              ["Поддержка", "чат и тикеты внутри платформы"],
            ].map(([title, text]) => (
              <div key={title} className="rounded-2xl bg-paper p-5">
                <p className="display text-lg">{title}</p>
                <p className="mt-1 text-sm text-ink-3">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* -------------------------------- FAQ ---------------------------------- */

const FAQ = [
  [
    "Сколько стоит подбор?",
    "Подбор и заявка бесплатны. Вы платите только за уроки, цену назначает репетитор — она видна в каталоге.",
  ],
  [
    "Что если репетитор не подошёл?",
    "Можно взять пробный урок и сменить преподавателя. Оплата за непроведённые уроки возвращается по правилам площадки.",
  ],
  [
    "Как проходят занятия?",
    "Онлайн, один на один, по видеосвязи внутри платформы. Расписание и переносы — в календаре.",
  ],
  [
    "Чем это отличается от обычного каталога?",
    "Мы начинаем не с поиска, а с заявки: несколько вопросов о вас и контакт для связи — и мы сами подбираем репетитора и перезваниваем, вместо того чтобы сразу бросать в каталог.",
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
          Начните с одного вопроса: чему вы хотите научиться?
        </h2>
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/onboarding" className="btn btn-primary">
            Пройти подбор
          </Link>
          <Link href="/tutors" className="btn btn-ghost">
            Смотреть каталог
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
