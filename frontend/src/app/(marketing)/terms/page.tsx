export const metadata = { title: "Условия использования — EduBridge" };

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Документы</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Условия использования</h1>
        <p className="mt-3 text-sm text-ink-3">Действует с {new Date().toLocaleDateString("ru-RU")}.</p>
      </header>

      <div className="prose mt-8 space-y-6 text-sm leading-relaxed text-ink-2">
        <section>
          <h2 className="display text-lg">1. Общие положения</h2>
          <p className="mt-2">
            Используя EduBridge, вы соглашаетесь с этими условиями. Платформа предоставляет доступ
            к личному кабинету для занятий на курсе: расписание, переписка с преподавателем,
            AI-помощник и учебные материалы.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">2. Аккаунты</h2>
          <p className="mt-2">
            Самостоятельная регистрация на платформе не предусмотрена — аккаунт создаётся
            администратором. Вы отвечаете за сохранность пароля и всё, что происходит под вашим
            аккаунтом.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">3. Занятия и видеосвязь</h2>
          <p className="mt-2">
            Видеозанятия проходят через встроенный видеосервис платформы (LiveKit) прямо в личном
            кабинете. Платформа не несёт ответственности за перебои в работе интернет-соединения
            или сторонних сервисов видеосвязи.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">4. Правила поведения</h2>
          <p className="mt-2">
            Запрещено использовать платформу для рассылки спама, оскорблений, передачи незаконного
            контента. Администрация вправе ограничить доступ к аккаунту при нарушении этих правил.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">5. Изменения условий</h2>
          <p className="mt-2">
            Мы можем обновлять эти условия; актуальная версия всегда доступна на этой странице.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">6. Контакты</h2>
          <p className="mt-2">По вопросам — через форму обратной связи на сайте.</p>
        </section>
      </div>
    </div>
  );
}
