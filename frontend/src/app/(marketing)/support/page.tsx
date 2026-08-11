export const metadata = { title: "Поддержка — EduBridge" };

export default function SupportPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Помощь</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Поддержка</h1>
      </header>

      <div className="mt-8 space-y-6 text-sm leading-relaxed text-ink-2">
        <section className="card p-6">
          <h2 className="display text-lg">Если у вас есть аккаунт</h2>
          <p className="mt-2">
            Войдите в личный кабинет — раздел «Сообщения» для вопросов преподавателю, «Тикеты» (для
            сотрудников) для остальных обращений в поддержку платформы.
          </p>
        </section>

        <section className="card p-6">
          <h2 className="display text-lg">Если аккаунта ещё нет</h2>
          <p className="mt-2">
            Оставьте заявку на{" "}
            <a href="/onboarding" className="text-aurora-700 underline">
              главной странице
            </a>
            , и мы свяжемся с вами по указанному телефону или email.
          </p>
        </section>

        <section className="card p-6">
          <h2 className="display text-lg">Проблемы с подключением Zoom</h2>
          <p className="mt-2">
            Если видеовстречи Zoom не создаются или не получается подключить аккаунт Zoom в
            настройках — напишите об этом через «Сообщения» или тикет с описанием проблемы.
          </p>
        </section>
      </div>
    </div>
  );
}
