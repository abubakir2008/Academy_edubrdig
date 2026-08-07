/**
 * The 7-department subject tree: what `/tutors` filters by (`category`/
 * `language`), what the tutor profile editor picks specializations from, and
 * what the footer links to. The onboarding intake form (`onboarding/`) is a
 * separate, fixed question set — see `./onboarding.ts` — it only borrows the
 * language list from here, it doesn't walk this tree.
 */

export type Option = { id: string; label: string; hint?: string; emoji?: string };

export type Category = {
  id: string;
  label: string;
  emoji: string;
  tagline: string;
  /** Language categories filter by `language`; the rest by `category`. */
  mapsTo: "language" | "category";
  subjectTitle: string;
  subjects: Option[];
  goals: Option[];
  levelTitle: string;
  levels: Option[];
};

export const CATEGORIES: Category[] = [
  {
    id: "languages",
    label: "Иностранные языки",
    emoji: "🗣️",
    tagline: "Говорить свободно — с носителями и практиками",
    mapsTo: "language",
    subjectTitle: "Какой язык учим?",
    subjects: [
      { id: "english", label: "Английский", emoji: "🇬🇧" },
      { id: "russian", label: "Русский", emoji: "🇷🇺" },
      { id: "kyrgyz", label: "Кыргызский", emoji: "🇰🇬" },
      { id: "turkish", label: "Турецкий", emoji: "🇹🇷" },
      { id: "chinese", label: "Китайский", emoji: "🇨🇳" },
      { id: "german", label: "Немецкий", emoji: "🇩🇪" },
      { id: "french", label: "Французский", emoji: "🇫🇷" },
      { id: "arabic", label: "Арабский", emoji: "🇦🇪" },
      { id: "korean", label: "Корейский", emoji: "🇰🇷" },
    ],
    goals: [
      { id: "speaking", label: "Разговорная практика", hint: "снять языковой барьер", emoji: "💬" },
      { id: "exam", label: "Экзамен или сертификат", hint: "IELTS, TOEFL, ОРТ", emoji: "🎓" },
      { id: "work", label: "Работа и карьера", hint: "собеседования, переписка", emoji: "💼" },
      { id: "relocation", label: "Переезд или учёба за рубежом", emoji: "✈️" },
      { id: "school", label: "Помощь со школьной программой", emoji: "📚" },
      { id: "hobby", label: "Для себя, в удовольствие", emoji: "🌱" },
    ],
    levelTitle: "Какой у вас сейчас уровень?",
    levels: [
      { id: "a0", label: "С нуля", hint: "не знаю ни слова" },
      { id: "a1_a2", label: "Начальный (A1–A2)", hint: "простые фразы" },
      { id: "b1_b2", label: "Средний (B1–B2)", hint: "говорю, но с ошибками" },
      { id: "c1_c2", label: "Продвинутый (C1–C2)", hint: "нужен нюанс и беглость" },
      { id: "unknown", label: "Не знаю", hint: "определим на пробном уроке" },
    ],
  },
  {
    id: "school",
    label: "Школьная программа",
    emoji: "📐",
    tagline: "Подтянуть предмет и вернуть уверенность",
    mapsTo: "category",
    subjectTitle: "По какому предмету нужна помощь?",
    subjects: [
      { id: "math", label: "Математика", emoji: "➗" },
      { id: "physics", label: "Физика", emoji: "🧲" },
      { id: "chemistry", label: "Химия", emoji: "⚗️" },
      { id: "biology", label: "Биология", emoji: "🧬" },
      { id: "informatics", label: "Информатика", emoji: "💻" },
      { id: "history", label: "История", emoji: "🏛️" },
      { id: "geography", label: "География", emoji: "🗺️" },
      { id: "literature", label: "Литература", emoji: "📖" },
    ],
    goals: [
      { id: "grades", label: "Исправить оценки", hint: "текущая успеваемость", emoji: "📈" },
      { id: "catchup", label: "Догнать пропущенное", emoji: "⏱️" },
      { id: "exam", label: "Подготовка к ОРТ / ЕГЭ", emoji: "🎯" },
      { id: "olympiad", label: "Олимпиады и углублённый уровень", emoji: "🏅" },
      { id: "confidence", label: "Понять предмет с нуля", emoji: "💡" },
    ],
    levelTitle: "В каком классе ученик?",
    levels: [
      { id: "1_4", label: "1–4 класс" },
      { id: "5_8", label: "5–8 класс" },
      { id: "9", label: "9 класс" },
      { id: "10_11", label: "10–11 класс" },
      { id: "graduate", label: "Выпускник / готовлюсь отдельно" },
    ],
  },
  {
    id: "exams",
    label: "Экзамены и поступление",
    emoji: "🎯",
    tagline: "Балл, который открывает нужную дверь",
    mapsTo: "category",
    subjectTitle: "К какому экзамену готовимся?",
    subjects: [
      { id: "ort", label: "ОРТ", emoji: "🇰🇬" },
      { id: "ielts", label: "IELTS", emoji: "🇬🇧" },
      { id: "toefl", label: "TOEFL", emoji: "🇺🇸" },
      { id: "sat", label: "SAT", emoji: "📊" },
      { id: "ege", label: "ЕГЭ", emoji: "🇷🇺" },
      { id: "ent", label: "ЕНТ", emoji: "🇰🇿" },
      { id: "university", label: "Вступительные вуза", emoji: "🏫" },
    ],
    goals: [
      { id: "grant", label: "Грант или бюджетное место", emoji: "🎖️" },
      { id: "target_score", label: "Нужен конкретный балл", emoji: "🎯" },
      { id: "abroad", label: "Поступление за рубеж", emoji: "🌍" },
      { id: "retake", label: "Пересдача", emoji: "🔁" },
    ],
    levelTitle: "Сколько времени до экзамена?",
    levels: [
      { id: "lt1m", label: "Меньше месяца", hint: "нужен интенсив" },
      { id: "1_3m", label: "1–3 месяца" },
      { id: "3_6m", label: "3–6 месяцев" },
      { id: "gt6m", label: "Больше полугода", hint: "спокойный темп" },
    ],
  },
  {
    id: "it",
    label: "IT и программирование",
    emoji: "⌨️",
    tagline: "От первой строчки кода до оффера",
    mapsTo: "category",
    subjectTitle: "Что хотите освоить?",
    subjects: [
      { id: "python", label: "Python", emoji: "🐍" },
      { id: "javascript", label: "JavaScript / React", emoji: "⚛️" },
      { id: "backend", label: "Backend и базы данных", emoji: "🗄️" },
      { id: "data_science", label: "Data Science / ML", emoji: "📊" },
      { id: "qa", label: "Тестирование (QA)", emoji: "🐞" },
      { id: "uiux", label: "UI/UX дизайн", emoji: "🎨" },
      { id: "mobile", label: "Мобильная разработка", emoji: "📱" },
    ],
    goals: [
      { id: "career_switch", label: "Сменить профессию", emoji: "🚀" },
      { id: "first_job", label: "Найти первую работу", emoji: "💼" },
      { id: "level_up", label: "Вырасти в текущей роли", emoji: "📈" },
      { id: "project", label: "Довести свой проект", emoji: "🛠️" },
      { id: "interview", label: "Подготовиться к собеседованию", emoji: "🗣️" },
    ],
    levelTitle: "Ваш текущий опыт?",
    levels: [
      { id: "zero", label: "С нуля" },
      { id: "basics", label: "Знаю основы", hint: "проходил курсы" },
      { id: "practice", label: "Пишу код на практике" },
      { id: "pro", label: "Работаю в IT", hint: "нужен точечный апгрейд" },
    ],
  },
  {
    id: "business",
    label: "Бизнес и карьера",
    emoji: "📈",
    tagline: "Навыки, которые видно в результатах",
    mapsTo: "category",
    subjectTitle: "Какое направление?",
    subjects: [
      { id: "marketing", label: "Маркетинг", emoji: "📣" },
      { id: "finance", label: "Финансы и учёт", emoji: "💰" },
      { id: "management", label: "Менеджмент", emoji: "🧭" },
      { id: "public_speaking", label: "Публичные выступления", emoji: "🎤" },
      { id: "excel", label: "Excel / аналитика", emoji: "📊" },
      { id: "sales", label: "Продажи и переговоры", emoji: "🤝" },
    ],
    goals: [
      { id: "own_business", label: "Развиваю свой бизнес", emoji: "🏪" },
      { id: "promotion", label: "Хочу повышение", emoji: "⬆️" },
      { id: "team", label: "Обучаю команду", emoji: "👥" },
      { id: "skills", label: "Закрыть пробелы в навыках", emoji: "🧩" },
    ],
    levelTitle: "Насколько глубоко погружены?",
    levels: [
      { id: "zero", label: "Совсем новичок" },
      { id: "basics", label: "Базовое понимание" },
      { id: "practitioner", label: "Практикую каждый день" },
      { id: "expert", label: "Нужен уровень эксперта" },
    ],
  },
  {
    id: "creative",
    label: "Музыка и творчество",
    emoji: "🎸",
    tagline: "Занятие, ради которого ждёшь вечера",
    mapsTo: "category",
    subjectTitle: "Чем хотите заниматься?",
    subjects: [
      { id: "guitar", label: "Гитара", emoji: "🎸" },
      { id: "piano", label: "Фортепиано", emoji: "🎹" },
      { id: "vocal", label: "Вокал", emoji: "🎤" },
      { id: "komuz", label: "Комуз", emoji: "🪕" },
      { id: "drawing", label: "Рисование", emoji: "🖌️" },
      { id: "photo", label: "Фото и видео", emoji: "📷" },
    ],
    goals: [
      { id: "hobby", label: "Для удовольствия", emoji: "🌿" },
      { id: "stage", label: "Выступать на сцене", emoji: "🎭" },
      { id: "school", label: "Поступление в творческий вуз", emoji: "🏛️" },
      { id: "portfolio", label: "Собрать портфолио", emoji: "🗂️" },
    ],
    levelTitle: "Ваш опыт?",
    levels: [
      { id: "zero", label: "Никогда не пробовал" },
      { id: "some", label: "Немного занимался" },
      { id: "regular", label: "Занимаюсь регулярно" },
      { id: "advanced", label: "Продвинутый уровень" },
    ],
  },
  {
    id: "kids",
    label: "Детям и дошкольникам",
    emoji: "🧸",
    tagline: "Мягкий старт без слёз и зубрёжки",
    mapsTo: "category",
    subjectTitle: "Что нужно ребёнку?",
    subjects: [
      { id: "reading", label: "Чтение и письмо", emoji: "✏️" },
      { id: "math_kids", label: "Счёт и логика", emoji: "🔢" },
      { id: "speech", label: "Логопед / речь", emoji: "🗣️" },
      { id: "english_kids", label: "Английский для малышей", emoji: "🧩" },
      { id: "school_prep", label: "Подготовка к школе", emoji: "🎒" },
    ],
    goals: [
      { id: "school_ready", label: "Подготовить к первому классу", emoji: "🎒" },
      { id: "interest", label: "Заинтересовать предметом", emoji: "✨" },
      { id: "speech_fix", label: "Поставить речь", emoji: "🔤" },
      { id: "develop", label: "Общее развитие", emoji: "🌱" },
    ],
    levelTitle: "Сколько лет ребёнку?",
    levels: [
      { id: "3_4", label: "3–4 года" },
      { id: "5_6", label: "5–6 лет" },
      { id: "7_9", label: "7–9 лет" },
      { id: "10_12", label: "10–12 лет" },
    ],
  },
];

export const categoryById = (id: string | undefined) =>
  CATEGORIES.find((c) => c.id === id);
