/** Plain data module (no "use client") — shared between the server page.tsx
 * (FAQPage JSON-LD) and the client home-content.tsx (the rendered <details>
 * list). A data export can't be imported from a "use client" module into a
 * Server Component — only components cross that boundary — so it lives here
 * instead of inside home-content.tsx. */
export const FAQ: [string, string][] = [
  [
    "Как получить доступ?",
    "Регистрация в один клик недоступна — аккаунт создаёт администратор площадки и выдаёт данные для входа.",
  ],
  [
    "С кем я буду переписываться?",
    "С преподавателем или наставником, к которому вас прикрепил администратор — чат доступен сразу в кабинете.",
  ],
  [
    "Как проходят занятия?",
    "Каждое занятие курса — это Zoom-встреча по расписанию; ссылка появляется в кабинете, преподаватель подключает свой Zoom-аккаунт заранее.",
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
