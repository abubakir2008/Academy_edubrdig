/**
 * Config for the onboarding intake form (`/onboarding`). This is a fixed,
 * six-step lead form — not a catalog filter — so it lives separately from
 * `catalog.ts`. "Where do you study" and "why" are editable from
 * `/dashboard/admin` (they're `Category` rows with `group="university"` /
 * `group="goal"`, fetched from the public `GET /admin/categories`); these
 * local lists are only the fallback for when that call fails.
 */

import { categoryById, type Option } from "./catalog";

export const LANGUAGES: Option[] = categoryById("languages")!.subjects;

export const GOALS_FALLBACK: Option[] = [
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
