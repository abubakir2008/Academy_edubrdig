export const metadata = { title: "Политика конфиденциальности — EduBridge" };

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Документы</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Политика конфиденциальности</h1>
        <p className="mt-3 text-sm text-ink-3">Действует с {new Date().toLocaleDateString("ru-RU")}.</p>
      </header>

      <div className="prose mt-8 space-y-6 text-sm leading-relaxed text-ink-2">
        <section>
          <h2 className="display text-lg">1. Кто мы</h2>
          <p className="mt-2">
            EduBridge — образовательная платформа для занятий с преподавателем: курсы, расписание
            занятий, переписка и учебные материалы. Оператор платформы находится в Кыргызской
            Республике.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">2. Какие данные мы собираем</h2>
          <p className="mt-2">
            Имя, email и телефон — при заявке через форму на сайте или при создании аккаунта
            администратором; данные профиля (имя, аватар); переписка с преподавателем и
            AI-помощником; расписание и записи о занятиях, включая данные, необходимые для
            создания видеовстречи (Zoom); технические данные (IP-адрес, тип устройства) для защиты
            от злоупотреблений.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">3. Как мы используем данные</h2>
          <p className="mt-2">
            Для предоставления доступа к личному кабинету, организации занятий и переписки,
            отправки уведомлений о занятиях и сообщениях, связи с вами по заявке с сайта. Мы не
            продаём персональные данные третьим лицам.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">4. Сторонние сервисы</h2>
          <p className="mt-2">
            Для видеозанятий платформа использует Zoom: при создании урока преподавателем на его
            собственном привязанном аккаунте Zoom создаётся встреча, доступ к которой получают он и
            ученики этого курса. Мы не запрашиваем доступ к аккаунту Zoom ученика.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">5. Хранение и удаление</h2>
          <p className="mt-2">
            Данные хранятся, пока аккаунт активен. Чтобы запросить удаление своих данных, напишите
            на контактный email платформы.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">6. Контакты</h2>
          <p className="mt-2">
            По вопросам, связанным с этой политикой, — через форму обратной связи на сайте.
          </p>
        </section>
      </div>
    </div>
  );
}
