"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { get } from "@/lib/api";
import type { AdminUser, Course, Lesson, LessonStatus } from "@/lib/types";

const STATUS_LABEL: Record<LessonStatus, string> = {
  scheduled: "Запланировано",
  completed: "Проведено",
  cancelled: "Отменено",
  missed: "Не состоялось",
};

const STATUS_ORDER: LessonStatus[] = ["completed", "missed", "cancelled", "scheduled"];

type Counts = Record<LessonStatus, number> & { total: number };

function emptyCounts(): Counts {
  return { total: 0, scheduled: 0, completed: 0, cancelled: 0, missed: 0 };
}

function tally(lessons: Lesson[]): Counts {
  const c = emptyCounts();
  for (const l of lessons) {
    c.total += 1;
    c[l.status] += 1;
  }
  return c;
}

function groupBy(lessons: Lesson[], key: (l: Lesson) => string): Map<string, Lesson[]> {
  const map = new Map<string, Lesson[]>();
  for (const l of lessons) {
    const k = key(l);
    const bucket = map.get(k);
    if (bucket) bucket.push(l);
    else map.set(k, [l]);
  }
  return map;
}

/**
 * Read-only lesson analytics for staff — no dedicated backend endpoint:
 * /calendar/lessons (staff, unfiltered) already returns every lesson with
 * its computed status (see calendar's _lesson_out), so this just joins
 * that against /courses and /auth/admin/users (both already staff-only)
 * client-side instead of adding a new cross-department aggregation route.
 */
export default function LessonAnalyticsPage() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [l, c, u] = await Promise.all([
      get<Lesson[]>("/calendar/lessons", true).catch(() => [] as Lesson[]),
      get<Course[]>("/courses", true).catch(() => [] as Course[]),
      get<AdminUser[]>("/auth/admin/users", true).catch(() => [] as AdminUser[]),
    ]);
    setLessons(l);
    setCourses(c);
    setUsers(u);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const courseTitle = useMemo(() => {
    const byId = new Map(courses.map((c) => [c.id, c.title]));
    return (id: string) => byId.get(id) ?? "Курс удалён";
  }, [courses]);

  const teacherName = useMemo(() => {
    const byId = new Map(users.map((u) => [u.id, u.full_name || u.email]));
    return (id: string) => byId.get(id) ?? "Репетитор удалён";
  }, [users]);

  const overall = useMemo(() => tally(lessons), [lessons]);

  const byCourse = useMemo(() => {
    const groups = groupBy(lessons, (l) => l.course_id);
    return Array.from(groups.entries())
      .map(([courseId, ls]) => ({ id: courseId, title: courseTitle(courseId), counts: tally(ls) }))
      .sort((a, b) => b.counts.total - a.counts.total);
  }, [lessons, courseTitle]);

  const byTeacher = useMemo(() => {
    const groups = groupBy(lessons, (l) => l.teacher_id);
    return Array.from(groups.entries())
      .map(([teacherId, ls]) => ({ id: teacherId, name: teacherName(teacherId), counts: tally(ls) }))
      .sort((a, b) => b.counts.total - a.counts.total);
  }, [lessons, teacherName]);

  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Админ</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Аналитика уроков</h1>
        </div>
        <Link href="/dashboard/admin" className="btn btn-ghost">
          ← Панель управления
        </Link>
      </header>

      {loading ? (
        <p className="mt-8 text-sm text-ink-3">Загрузка…</p>
      ) : lessons.length === 0 ? (
        <p className="card mt-8 p-6 text-sm text-ink-3">Уроков пока нет.</p>
      ) : (
        <>
          <section className="mt-8 grid gap-4 sm:grid-cols-5">
            <StatTile label="Всего уроков" value={overall.total} />
            {STATUS_ORDER.map((s) => (
              <StatTile key={s} label={STATUS_LABEL[s]} value={overall[s]} />
            ))}
          </section>

          <section className="mt-10">
            <h2 className="display text-lg">По курсам</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs text-ink-3">
                    <th className="py-2 pr-4 font-medium">Курс</th>
                    <th className="py-2 pr-4 font-medium">Всего</th>
                    {STATUS_ORDER.map((s) => (
                      <th key={s} className="py-2 pr-4 font-medium">
                        {STATUS_LABEL[s]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {byCourse.map((row) => (
                    <tr key={row.id} className="border-b border-line/60">
                      <td className="py-2.5 pr-4 font-semibold">{row.title}</td>
                      <td className="py-2.5 pr-4">{row.counts.total}</td>
                      {STATUS_ORDER.map((s) => (
                        <td key={s} className="py-2.5 pr-4 text-ink-2">
                          {row.counts[s]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-10">
            <h2 className="display text-lg">По учителям</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs text-ink-3">
                    <th className="py-2 pr-4 font-medium">Учитель</th>
                    <th className="py-2 pr-4 font-medium">Всего</th>
                    {STATUS_ORDER.map((s) => (
                      <th key={s} className="py-2 pr-4 font-medium">
                        {STATUS_LABEL[s]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {byTeacher.map((row) => (
                    <tr key={row.id} className="border-b border-line/60">
                      <td className="py-2.5 pr-4 font-semibold">{row.name}</td>
                      <td className="py-2.5 pr-4">{row.counts.total}</td>
                      {STATUS_ORDER.map((s) => (
                        <td key={s} className="py-2.5 pr-4 text-ink-2">
                          {row.counts[s]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="card p-5">
      <p className="text-xs text-ink-3">{label}</p>
      <p className="display mt-1 text-2xl">{value}</p>
    </div>
  );
}
