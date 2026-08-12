import type { Metadata } from "next";

import { FAQ } from "./faq-data";
import { HomeContent } from "./home-content";

const TITLE = "EduBridge — учитесь с наставником, не в одиночку";
const DESCRIPTION =
  "Личный кабинет для занятий на курсе: сообщения с преподавателем, занятия в Zoom по расписанию и AI-помощник для домашних заданий.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/" },
  twitter: { title: TITLE, description: DESCRIPTION },
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
