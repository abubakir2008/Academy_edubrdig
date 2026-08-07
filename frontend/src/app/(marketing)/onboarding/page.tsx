import { Suspense } from "react";

import { OnboardingWizard } from "./wizard";

export const metadata = {
  title: "Оставить заявку",
  description: "Расскажите, что хотите изучать — мы подберём репетитора и свяжемся с вами.",
};

export default function OnboardingPage() {
  return (
    <Suspense fallback={<div className="min-h-[60vh]" />}>
      <OnboardingWizard />
    </Suspense>
  );
}
