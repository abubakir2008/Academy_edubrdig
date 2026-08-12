import type { Metadata } from "next";

import { FAQ } from "./faq-data";
import { HomeContent } from "./home-content";

// No "EduBridge" here — the root layout's title template ("%s · EduBridge")
// already appends it; including it in both would render as "EduBridge — X
// · EduBridge". openGraph/twitter titles bypass that template, so they get
// the full brand statement instead.
const PAGE_TITLE = "Учитесь с наставником, не в одиночку";
const SOCIAL_TITLE = "EduBridge — учитесь с наставником, не в одиночку";
const DESCRIPTION =
  "Личный кабинет для занятий на курсе: сообщения с преподавателем, занятия в Zoom по расписанию и AI-помощник для домашних заданий.";

export const metadata: Metadata = {
  title: PAGE_TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/" },
  // openGraph/twitter are replaced wholesale (not deep-merged) when a page
  // redefines them, so every field the root layout set has to be repeated
  // here too — e.g. omitting `card` would silently downgrade Twitter's
  // preview from a large image card back to the default small one.
  openGraph: { title: SOCIAL_TITLE, description: DESCRIPTION, url: "/", type: "website", siteName: "EduBridge", locale: "ru_RU" },
  twitter: { card: "summary_large_image", title: SOCIAL_TITLE, description: DESCRIPTION },
};

// Organization + FAQPage structured data — FAQ is the same array
// home-content.tsx actually renders (see faq-data.ts), not a duplicate,
// so this just describes it to search engines for a potential rich result.
function JsonLd() {
  const data = [
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "EduBridge",
      url: "https://academy.edubridge.bond",
      logo: "https://academy.edubridge.bond/icon.png",
    },
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: FAQ.map(([question, answer]) => ({
        "@type": "Question",
        name: question,
        acceptedAnswer: { "@type": "Answer", text: answer },
      })),
    },
  ];
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />;
}

export default function HomePage() {
  return (
    <>
      <JsonLd />
      <HomeContent />
    </>
  );
}
