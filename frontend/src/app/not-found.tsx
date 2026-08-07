import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-5 px-5 py-28 text-center">
      <p className="display text-6xl text-aurora-600">404</p>
      <h1 className="display text-3xl">Такой страницы нет</h1>
      <p className="text-ink-3">
        Возможно, репетитор скрыл анкету или ссылка устарела. Попробуйте начать с подбора.
      </p>
      <div className="mt-2 flex flex-wrap justify-center gap-3">
        <Link href="/onboarding" className="btn btn-primary">
          Пройти подбор
        </Link>
        <Link href="/tutors" className="btn btn-ghost">
          В каталог
        </Link>
      </div>
    </div>
  );
}
