"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LessonsCalendar } from "@/components/lessons-calendar";
import { MyStudents } from "@/components/my-students";
import { NextLessonCard } from "@/components/next-lesson-card";
import { get } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Course } from "@/lib/types";

/** Overview tab: a simple welcome — students/tutors go straight to Messages
 * or the AI assistant, staff roles use their own tabs in the sidebar. */
export function DashboardOverview() {
  const { user } = useAuth();
  // Fetched once here and passed down — LessonsCalendar and MyStudents both
  // need the same /courses/me list; fetching it in each duplicated the call
  // on every visit to this page. `null` means "not loaded yet", distinct
  // from `[]` (loaded, tutor genuinely has no courses).
  const [courses, setCourses] = useState<Course[] | null>(null);
  const isStaff = user ? user.role !== "student" && user.role !== "tutor" : false;

  useEffect(() => {
    if (!user || isStaff) return;
    get<Course[]>("/courses/me", true)
      .then(setCourses)
      .catch(() => setCourses([]));
  }, [user, isStaff]);

  if (!user) return null;

  return (
    <div className="mx-auto max-w-5xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">
          Обзор
        </p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">
          Привет, {user.full_name || user.email}
        </h1>
      </header>

      {isStaff ? (
        <div className="card mt-8 p-6 text-sm">
          <b className="font-semibold">Роль: {user.role}.</b> Ваши инструменты — во вкладках снизу
          (Админ, Тикеты и т.д., в зависимости от роли), не здесь на общем обзоре.
        </div>
      ) : (
        <>
          <LessonsCalendar courses={courses} />
          <NextLessonCard courses={courses} />
          {user.role === "tutor" && <MyStudents courses={courses} />}
          <div className="mt-8 grid gap-6 sm:grid-cols-2">
            <Link href="/dashboard/messages" className="card p-6 transition-colors hover:border-aurora-300">
              <h2 className="display text-lg">Сообщения</h2>
              <p className="mt-2 text-sm text-ink-3">Переписка с преподавателем — вопросы, задания, файлы.</p>
            </Link>
            <Link href="/dashboard/ai" className="card p-6 transition-colors hover:border-aurora-300">
              <h2 className="display text-lg">AI-помощник</h2>
              <p className="mt-2 text-sm text-ink-3">Генерация домашних заданий и объяснение тем.</p>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
