import { Suspense } from "react";

import { PaymentsView } from "./view";

export const metadata = { title: "Оплата" };

export default function PaymentsPage() {
  return (
    <Suspense fallback={<div className="min-h-[60vh]" />}>
      <PaymentsView />
    </Suspense>
  );
}
