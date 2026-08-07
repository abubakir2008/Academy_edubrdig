import { Suspense } from "react";

import { TutorCatalog } from "./catalog";

export const metadata = {
  title: "Каталог репетиторов",
  description: "Фильтруйте по предмету, языку, цене, опыту и рейтингу — и выбирайте репетитора.",
};

export default function TutorsPage() {
  return (
    <Suspense fallback={<div className="min-h-[60vh]" />}>
      <TutorCatalog />
    </Suspense>
  );
}
