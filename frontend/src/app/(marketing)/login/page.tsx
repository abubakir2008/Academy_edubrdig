import { Suspense } from "react";

import { LoginForm } from "./form";

export const metadata = { title: "Вход" };

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-[60vh]" />}>
      <LoginForm />
    </Suspense>
  );
}
