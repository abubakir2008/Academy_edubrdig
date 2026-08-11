export const metadata = { title: "Интеграция с Zoom — EduBridge" };

export default function ZoomDocsPage() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Документация</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Интеграция с Zoom</h1>
        <p className="mt-3 text-sm text-ink-3">
          Как преподаватель подключает свой аккаунт Zoom к EduBridge, как это используется и как
          отключить интеграцию.
        </p>
      </header>

      <div className="prose mt-8 space-y-6 text-sm leading-relaxed text-ink-2">
        <section>
          <h2 className="display text-lg">Зачем это нужно</h2>
          <p className="mt-2">
            Каждое занятие на курсе — это реальная встреча Zoom. Она создаётся автоматически на{" "}
            <b>собственном</b> Zoom-аккаунте преподавателя в момент добавления урока в расписание —
            платформа не использует общий/служебный Zoom-аккаунт.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">Как подключить (Add)</h2>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            <li>Войдите в личный кабинет как преподаватель на academy.edubridge.bond.</li>
            <li>
              Откройте раздел <b>Настройки</b> (Settings) в боковом меню.
            </li>
            <li>
              В блоке «Zoom» нажмите <b>«Подключить Zoom»</b>.
            </li>
            <li>Вы будете перенаправлены на страницу авторизации Zoom (oauth/authorize).</li>
            <li>Войдите в свой аккаунт Zoom и разрешите доступ приложению EduBridge.</li>
            <li>
              После подтверждения вы вернётесь в личный кабинет — статус изменится на «✓ Подключено»
              с адресом вашей Zoom-почты.
            </li>
          </ol>
        </section>

        <section>
          <h2 className="display text-lg">Как это используется (Use)</h2>
          <p className="mt-2">
            При создании урока в расписании курса EduBridge через Zoom API создаёт встречу на
            аккаунте преподавателя и сохраняет ссылку на подключение. Эта ссылка видна
            преподавателю и записанным на курс ученикам в их личном кабинете (календарь занятий). При
            переносе или отмене урока встреча в Zoom обновляется/удаляется тем же образом.
          </p>
        </section>

        <section>
          <h2 className="display text-lg">Как отключить (Remove)</h2>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            <li>
              В личном кабинете откройте <b>Настройки</b>.
            </li>
            <li>
              В блоке «Zoom» нажмите <b>«Отключить»</b>.
            </li>
            <li>
              Связь аккаунта Zoom с EduBridge удаляется на нашей стороне немедленно; уже созданные
              встречи для будущих уроков нужно будет отключить также в настройках приложений вашего
              аккаунта Zoom (Zoom → Settings → Connected Apps), если требуется полностью отозвать
              доступ.
            </li>
          </ol>
        </section>

        <section>
          <h2 className="display text-lg">Права (scopes)</h2>
          <p className="mt-2">
            Приложению нужны права на создание, изменение и удаление встреч (Meetings) — без них
            платформа не сможет создавать видеовстречи для уроков.
          </p>
        </section>
      </div>
    </div>
  );
}
