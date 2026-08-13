"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Bell,
  BookOpen,
  Calendar,
  LifeBuoy,
  LogIn,
  MessageSquare,
  Plus,
  Send,
  Sparkles,
  UserCog,
  Video,
} from "lucide-react";

import { FAQ } from "./faq-data";

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.55, delay, ease: "easeOut" as const },
});

export function HomeContent() {
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

const HERO_PILLS = [
  { icon: BookOpen, label: "Курсы" },
  { icon: Video, label: "Видеозанятия" },
  { icon: MessageSquare, label: "Чат" },
  { icon: Sparkles, label: "AI-помощник" },
];

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-line">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-32 left-1/2 h-144 w-xl -translate-x-1/2 rounded-full opacity-40 blur-3xl"
        style={{ background: "radial-gradient(closest-side, var(--color-aurora-100), transparent)" }}
      />
      <div className="relative mx-auto max-w-7xl px-5 pb-16 pt-16 md:pb-24 md:pt-24">
        <motion.div className="mx-auto max-w-2xl text-center" {...fadeUp(0)}>
          <span className="chip mx-auto border-0! bg-aurora-100! text-aurora-700!">
            <span className="h-1.5 w-1.5 rounded-full bg-jade-500" />
            Личный кабинет для занятий на курсе
          </span>

          <h1 className="display mt-5 text-[clamp(2.4rem,6vw,4.2rem)]">
            Учитесь <span className="arc-underline">с наставником</span>, не в одиночку
          </h1>

          <p className="mt-6 text-lg leading-relaxed text-ink-2">
            Личные сообщения с преподавателем, видеозанятия по расписанию курса и AI-помощник для
            домашних заданий — всё в одном личном кабинете.
          </p>

          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Link href="/login" className="btn btn-primary">
              <LogIn className="h-4 w-4" aria-hidden />
              Войти в кабинет
            </Link>
            <Link href="/onboarding" className="btn btn-ghost">
              <Send className="h-4 w-4" aria-hidden />
              Оставить заявку
            </Link>
          </div>
        </motion.div>

        <motion.div
          className="mx-auto mt-14 flex max-w-3xl flex-wrap justify-center gap-3"
          {...fadeUp(0.15)}
        >
          {HERO_PILLS.map(({ icon: Icon, label }) => (
            <span
              key={label}
              className="inline-flex items-center gap-2 rounded-full border border-line bg-paper px-4 py-2 text-sm font-medium text-ink-2 shadow-lift"
            >
              <Icon className="h-4 w-4 text-aurora-600" aria-hidden />
              {label}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

/* ------------------------------ Features -------------------------------- */

const FEATURES = [
  {
    icon: MessageSquare,
    title: "Сообщения с преподавателем",
    text: "Личный чат с вложениями — обсуждайте задания и вопросы напрямую, без звонков и почты.",
    tone: "aurora",
  },
  {
    icon: Video,
    title: "Видеозанятия по расписанию",
    text: "Каждое занятие курса открывается прямо в личном кабинете — без стороннего приложения и ссылок для перехода.",
    tone: "citrus",
  },
  {
    icon: Sparkles,
    title: "AI-помощник",
    text: "Генерация домашних заданий, объяснение тем и разбор урока — доступно прямо в кабинете.",
    tone: "jade",
  },
  {
    icon: BookOpen,
    title: "Курсы и группа",
    text: "Курс — это один преподаватель и его группа. Прогресс, материалы и участники — на одной странице.",
    tone: "aurora",
  },
  {
    icon: Bell,
    title: "Уведомления в реальном времени",
    text: "Новое сообщение или занятие появляется в кабинете сразу, даже если вкладка свёрнута.",
    tone: "citrus",
  },
  {
    icon: LifeBuoy,
    title: "Поддержка",
    text: "Открывайте обращение прямо из кабинета — команда поддержки отвечает в том же чате.",
    tone: "jade",
  },
];

const TONE: Record<string, string> = {
  aurora: "bg-aurora-100 text-aurora-700",
  citrus: "bg-citrus-100 text-citrus-700",
  jade: "bg-jade-100 text-jade-700",
};

function Features() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-16" id="features">
      <SectionHead eyebrow="Что внутри" title="Всё нужное для занятий — в одном месте" />
      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <motion.div key={f.title} className="card card-hover p-6" {...fadeUp(i * 0.06)}>
            <span
              className={`flex h-12 w-12 items-center justify-center rounded-2xl ${TONE[f.tone]}`}
              aria-hidden
            >
              <f.icon className="h-6 w-6" strokeWidth={1.9} />
            </span>
            <h3 className="display mt-4 text-lg">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-3">{f.text}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

/* ---------------------------- How it works ----------------------------- */

const STEPS = [
  {
    icon: UserCog,
    title: "Получите доступ",
    text: "Аккаунт создаёт администратор площадки — вы получаете email и пароль для входа.",
  },
  {
    icon: LogIn,
    title: "Заходите в кабинет",
    text: "Сообщения, курс, расписание занятий и AI-помощник — всё сразу после входа.",
  },
  {
    icon: Calendar,
    title: "Занимайтесь по расписанию",
    text: "Присоединяйтесь к видеозанятиям по расписанию курса прямо в кабинете, общайтесь с преподавателем и группой.",
  },
];

function HowItWorks() {
  return (
    <section id="how" className="bg-paper-2 py-16">
      <div className="mx-auto max-w-7xl px-5">
        <SectionHead eyebrow="Как это работает" title="Три шага — и вы в кабинете" />

        <ol className="mt-10 grid gap-6 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <motion.li key={step.title} className="relative" {...fadeUp(index * 0.1)}>
              <span
                className="display flex h-12 w-12 items-center justify-center rounded-2xl text-white"
                style={{ background: "linear-gradient(135deg, var(--color-aurora-600), var(--color-aurora-900))" }}
              >
                <step.icon className="h-6 w-6" strokeWidth={1.9} aria-hidden />
              </span>
              <h3 className="display mt-4 text-xl">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-3">{step.text}</p>
              {index < STEPS.length - 1 && (
                <span
                  aria-hidden
                  className="absolute -right-3 top-6 hidden h-px w-6 border-t-2 border-dashed border-line md:block"
                />
              )}
            </motion.li>
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
        {VOICES.map((voice, i) => (
          <motion.figure key={voice.name} className="card flex flex-col gap-5 p-6" {...fadeUp(i * 0.08)}>
            <span className="display text-4xl leading-none text-aurora-300" aria-hidden>
              &ldquo;
            </span>
            <blockquote className="flex-1 leading-relaxed text-ink-2">{voice.quote}</blockquote>
            <figcaption className="border-t border-line pt-4 text-sm">
              <span className="font-semibold">{voice.name}</span>
              <span className="text-ink-3"> · {voice.role}</span>
            </figcaption>
          </motion.figure>
        ))}
      </div>
    </section>
  );
}

/* -------------------------------- FAQ ---------------------------------- */

function Faq() {
  return (
    <section className="mx-auto max-w-3xl px-5 py-16">
      <SectionHead eyebrow="Вопросы" title="Коротко о главном" center />
      <div className="mt-10 space-y-3">
        {FAQ.map(([question, answer]) => (
          <details key={question} className="card group p-5 [&_summary::-webkit-details-marker]:hidden">
            <summary className="flex cursor-pointer items-center justify-between gap-4 font-semibold">
              {question}
              <Plus
                className="h-4.5 w-4.5 shrink-0 text-aurora-600 transition-transform group-open:rotate-45"
                aria-hidden
              />
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
    <section className="mx-auto max-w-7xl px-5 pb-20">
      <motion.div
        className="relative overflow-hidden rounded-card p-12 text-white shadow-glow-lg"
        style={{ background: "linear-gradient(135deg, var(--color-aurora-600), var(--color-aurora-900))" }}
        {...fadeUp(0)}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-3xl"
        />
        <div className="relative grid gap-10 text-center sm:grid-cols-2 sm:text-left">
          <div className="flex flex-col items-center gap-4 sm:items-start">
            <h2 className="display text-[clamp(1.5rem,3vw,2rem)]">Данные для входа уже есть?</h2>
            <Link href="/login" className="btn bg-white text-aurora-700! hover:brightness-95">
              <LogIn className="h-4 w-4" aria-hidden />
              Войти в кабинет
            </Link>
          </div>
          <div className="flex flex-col items-center gap-4 border-t border-white/15 pt-10 sm:items-start sm:border-l sm:border-t-0 sm:pl-10 sm:pt-0">
            <h2 className="display text-[clamp(1.5rem,3vw,2rem)]">Ещё нет доступа?</h2>
            <Link
              href="/onboarding"
              className="btn btn-ghost bg-transparent! border-white/40! text-white! hover:bg-white/10! hover:border-white/40! hover:text-white!"
            >
              <Send className="h-4 w-4" aria-hidden />
              Оставить заявку
            </Link>
          </div>
        </div>
      </motion.div>
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
