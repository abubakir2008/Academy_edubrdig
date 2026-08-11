/**
 * Config for the public "leave a request" intake form (`/onboarding`) — the
 * only way a visitor with no account yet reaches staff, since this platform
 * has no self-registration (every account is admin-created). A fixed
 * six-step lead form, not a live filter — there's no admin-editable category
 * system anymore, so these lists are just static content.
 */

export type Option = { id: string; label: string; emoji?: string };

export type SubjectGroup = { id: string; label: string; emoji: string; subjects: Option[] };

export const SUBJECT_GROUPS: SubjectGroup[] = [
  {
    id: "languages",
    label: "Иностранные языки",
    emoji: "🗣️",
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
  },
  {
    id: "school",
    label: "Школьная программа",
    emoji: "📐",
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
  },
  {
    id: "exams",
    label: "Экзамены и поступление",
    emoji: "🎯",
    subjects: [
      { id: "ort", label: "ОРТ", emoji: "🇰🇬" },
      { id: "ielts", label: "IELTS", emoji: "🇬🇧" },
      { id: "toefl", label: "TOEFL", emoji: "🇺🇸" },
      { id: "sat", label: "SAT", emoji: "📊" },
      { id: "ege", label: "ЕГЭ", emoji: "🇷🇺" },
      { id: "ent", label: "ЕНТ", emoji: "🇰🇿" },
      { id: "university", label: "Вступительные вуза", emoji: "🏫" },
    ],
  },
  {
    id: "it",
    label: "IT и программирование",
    emoji: "⌨️",
    subjects: [
      { id: "python", label: "Python", emoji: "🐍" },
      { id: "javascript", label: "JavaScript / React", emoji: "⚛️" },
      { id: "backend", label: "Backend и базы данных", emoji: "🗄️" },
      { id: "data_science", label: "Data Science / ML", emoji: "📊" },
      { id: "qa", label: "Тестирование (QA)", emoji: "🐞" },
      { id: "uiux", label: "UI/UX дизайн", emoji: "🎨" },
      { id: "mobile", label: "Мобильная разработка", emoji: "📱" },
    ],
  },
  {
    id: "business",
    label: "Бизнес и карьера",
    emoji: "📈",
    subjects: [
      { id: "marketing", label: "Маркетинг", emoji: "📣" },
      { id: "finance", label: "Финансы и учёт", emoji: "💰" },
      { id: "management", label: "Менеджмент", emoji: "🧭" },
      { id: "public_speaking", label: "Публичные выступления", emoji: "🎤" },
      { id: "excel", label: "Excel / аналитика", emoji: "📊" },
      { id: "sales", label: "Продажи и переговоры", emoji: "🤝" },
    ],
  },
  {
    id: "creative",
    label: "Музыка и творчество",
    emoji: "🎸",
    subjects: [
      { id: "guitar", label: "Гитара", emoji: "🎸" },
      { id: "piano", label: "Фортепиано", emoji: "🎹" },
      { id: "vocal", label: "Вокал", emoji: "🎤" },
      { id: "komuz", label: "Комуз", emoji: "🪕" },
      { id: "drawing", label: "Рисование", emoji: "🖌️" },
      { id: "photo", label: "Фото и видео", emoji: "📷" },
    ],
  },
  {
    id: "kids",
    label: "Детям и дошкольникам",
    emoji: "🧸",
    subjects: [
      { id: "reading", label: "Чтение и письмо", emoji: "✏️" },
      { id: "math_kids", label: "Счёт и логика", emoji: "🔢" },
      { id: "speech", label: "Логопед / речь", emoji: "🗣️" },
      { id: "english_kids", label: "Английский для малышей", emoji: "🧩" },
      { id: "school_prep", label: "Подготовка к школе", emoji: "🎒" },
    ],
  },
];

export const GOALS: Option[] = [
  { id: "goal-personal", label: "Для себя" },
  { id: "goal-toefl", label: "TOEFL" },
  { id: "goal-ielts", label: "IELTS" },
  { id: "goal-study", label: "Учёба и школа" },
  { id: "goal-career", label: "Работа и карьера" },
  { id: "goal-other", label: "Другое" },
];

export const EUROPE_COUNTRIES: string[] = [
  "Австрия", "Албания", "Андорра", "Беларусь", "Бельгия", "Болгария",
  "Босния и Герцеговина", "Ватикан", "Великобритания", "Венгрия", "Германия",
  "Греция", "Дания", "Ирландия", "Исландия", "Испания", "Италия", "Кипр",
  "Латвия", "Литва", "Лихтенштейн", "Люксембург", "Мальта", "Молдова",
  "Монако", "Нидерланды", "Норвегия", "Польша", "Португалия", "Румыния",
  "Сан-Марино", "Северная Македония", "Сербия", "Словакия", "Словения",
  "Украина", "Финляндия", "Франция", "Хорватия", "Черногория", "Чехия",
  "Швейцария", "Швеция", "Эстония",
];

export const AMERICA_COUNTRIES: string[] = [
  "США", "Канада", "Мексика", "Бразилия", "Аргентина", "Чили", "Колумбия",
  "Перу", "Уругвай", "Парагвай", "Боливия", "Эквадор", "Венесуэла", "Куба",
  "Коста-Рика", "Панама", "Ямайка", "Доминиканская Республика", "Гватемала",
  "Гондурас",
];

export type LeadForm = {
  subject?: string;
  goal?: string;
  date_of_birth?: string;
  study_place?: string;
  destination_country?: string;
  full_name: string;
  contact_phone: string;
  contact_email: string;
};

export const emptyLeadForm: LeadForm = {
  full_name: "",
  contact_phone: "",
  contact_email: "",
};
