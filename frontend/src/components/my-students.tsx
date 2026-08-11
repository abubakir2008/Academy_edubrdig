"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MessageSquare, Users } from "lucide-react";

import { get, post } from "@/lib/api";
import { initials } from "@/lib/format";
import type { Course, CourseDetail } from "@/lib/types";

type Student = { id: string; name: string | null; courseTitle: string };

/**
 * Overview widget for a tutor: every student across all of their courses,
 * deduplicated, one click away from a chat — so they don't have to open a
 * course's roster just to message someone. Names come from the public
 * GET /users/{id} (same fallback-to-account-name resolution used on the
 * course detail page and in Messages). `courses` comes from the parent,
 * which fetches /courses/me once and shares it with LessonsCalendar too.
 */
export function MyStudents({ courses }: { courses: Course[] | null }) {
  const router = useRouter();
  const [students, setStudents] = useState<Student[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [messaging, setMessaging] = useState<string | null>(null);

  useEffect(() => {
    if (courses === null) return; // parent hasn't resolved /courses/me yet
    (async () => {
      const details = await Promise.all(
        courses.map((c) => get<CourseDetail>(`/courses/${c.id}`, true).catch(() => null)),
      );

      const byId = new Map<string, Student>();
      for (const detail of details) {
        if (!detail) continue;
        for (const sid of detail.student_ids) {
          if (!byId.has(sid)) byId.set(sid, { id: sid, name: null, courseTitle: detail.title });
        }
      }
      const list = Array.from(byId.values());
      setStudents(list);
      setLoaded(true);

      if (list.length === 0) return;
      // One batched round trip for every name instead of one GET /users/{id}
      // per student.
      const ids = list.map((s) => s.id).join(",");
      const profiles = await get<{ user_id: string; full_name: string | null }[]>(
        `/users/batch?ids=${encodeURIComponent(ids)}`,
      ).catch(() => [] as { user_id: string; full_name: string | null }[]);
      const nameById = new Map(profiles.map((p) => [p.user_id, p.full_name]));
      setStudents(list.map((s) => ({ ...s, name: nameById.get(s.id) ?? null })));
    })();
  }, [courses]);

  async function message(studentId: string) {
    setMessaging(studentId);
    try {
      await post("/chat/conversations", { peer_id: studentId }, true);
      router.push(`/dashboard/messages?peer=${studentId}`);
    } catch {
      setMessaging(null);
    }
  }

  if (!loaded) return null;

  return (
    <section className="card mt-8 p-6">
      <h2 className="display flex items-center gap-2 text-lg">
        <Users className="h-5 w-5 text-aurora-600" aria-hidden />
        Мои ученики ({students.length})
      </h2>

      {students.length === 0 ? (
        <p className="mt-3 text-sm text-ink-3">Пока нет учеников ни на одном курсе.</p>
      ) : (
        <ul className="mt-4 divide-y divide-line">
          {students.map((s) => {
            const name = s.name ?? "…";
            return (
              <li key={s.id} className="flex items-center justify-between gap-3 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-aurora-100 text-xs font-semibold text-aurora-700">
                    {initials(s.name)}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">{name}</span>
                    <span className="block truncate text-xs text-ink-3">{s.courseTitle}</span>
                  </span>
                </div>
                <button
                  className="btn btn-ghost shrink-0 !py-1.5 text-xs disabled:opacity-50"
                  disabled={messaging === s.id}
                  onClick={() => void message(s.id)}
                >
                  <MessageSquare className="h-3.5 w-3.5" aria-hidden />
                  Написать
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
