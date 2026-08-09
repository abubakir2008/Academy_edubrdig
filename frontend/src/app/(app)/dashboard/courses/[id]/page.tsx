"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { del, get, post, put } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AdminUser, CourseDetail } from "@/lib/types";

export default function CourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [tutors, setTutors] = useState<AdminUser[]>([]);
  const [students, setStudents] = useState<AdminUser[]>([]);
  const [titleDraft, setTitleDraft] = useState("");
  const [descriptionDraft, setDescriptionDraft] = useState("");
  const [addStudentId, setAddStudentId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isSuperAdmin = user?.role === "super_admin";

  const load = useCallback(async () => {
    const c = await get<CourseDetail>(`/courses/${id}`, true).catch(() => null);
    if (!c) {
      setNotFound(true);
      return;
    }
    setCourse(c);
    setTitleDraft(c.title);
    setDescriptionDraft(c.description ?? "");
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!isSuperAdmin) return;
    get<AdminUser[]>("/auth/admin/users?role=tutor", true).then(setTutors).catch(() => undefined);
    get<AdminUser[]>("/auth/admin/users?role=student", true).then(setStudents).catch(() => undefined);
  }, [isSuperAdmin]);

  async function saveDetails() {
    setError(null);
    try {
      await put(`/courses/${id}`, { title: titleDraft, description: descriptionDraft || null }, true);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить");
    }
  }

  async function assignTeacher(teacherId: string) {
    await put(`/courses/${id}/teacher`, { teacher_id: teacherId || null }, true).catch(() => undefined);
    await load();
  }

  async function addStudent() {
    if (!addStudentId) return;
    await post(`/courses/${id}/students`, { student_id: addStudentId }, true).catch(() => undefined);
    setAddStudentId("");
    await load();
  }

  async function removeStudent(studentId: string) {
    await del(`/courses/${id}/students/${studentId}`).catch(() => undefined);
    await load();
  }

  function nameFor(userId: string, pool: AdminUser[]): string {
    const match = pool.find((u) => u.id === userId);
    return match?.full_name || match?.email || userId.slice(0, 8);
  }

  if (notFound) {
    return (
      <div className="mx-auto max-w-4xl px-5 py-8 text-sm text-ink-3">Курс не найден или недоступен.</div>
    );
  }
  if (!course) return null;

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Курс</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">{course.title}</h1>
        </div>
        <Link href={`/dashboard/courses/${id}/calendar`} className="btn btn-primary">
          Уроки и календарь →
        </Link>
      </header>

      <section className="card mt-8 p-6">
        <h2 className="display text-lg">Основное</h2>
        {isSuperAdmin ? (
          <div className="mt-4 space-y-3">
            <input className="field" value={titleDraft} onChange={(e) => setTitleDraft(e.target.value)} />
            <textarea
              className="field min-h-24 resize-y"
              value={descriptionDraft}
              onChange={(e) => setDescriptionDraft(e.target.value)}
            />
            {error && <p className="text-sm text-coral-500">{error}</p>}
            <button className="btn btn-primary !py-2 text-sm" onClick={() => void saveDetails()}>
              Сохранить
            </button>
          </div>
        ) : (
          <p className="mt-2 text-sm text-ink-3">{course.description || "Без описания."}</p>
        )}
      </section>

      <section className="card mt-8 p-6">
        <h2 className="display text-lg">Учитель</h2>
        {isSuperAdmin ? (
          <select
            className="field mt-3"
            value={course.teacher_id ?? ""}
            onChange={(e) => void assignTeacher(e.target.value)}
          >
            <option value="">— не назначен —</option>
            {tutors.map((t) => (
              <option key={t.id} value={t.id}>
                {t.full_name || t.email}
              </option>
            ))}
          </select>
        ) : (
          <p className="mt-2 text-sm text-ink-3">
            {course.teacher_id ? nameFor(course.teacher_id, tutors) : "Не назначен"}
          </p>
        )}
      </section>

      <section className="card mt-8 p-6">
        <h2 className="display text-lg">Ученики ({course.student_ids.length})</h2>
        <ul className="mt-3 space-y-2">
          {course.student_ids.map((sid) => (
            <li key={sid} className="flex items-center justify-between gap-3 text-sm">
              <span>{nameFor(sid, students)}</span>
              {isSuperAdmin && (
                <button className="text-xs font-semibold text-coral-500" onClick={() => void removeStudent(sid)}>
                  Убрать
                </button>
              )}
            </li>
          ))}
          {course.student_ids.length === 0 && <p className="text-sm text-ink-3">Учеников пока нет.</p>}
        </ul>
        {isSuperAdmin && (
          <div className="mt-4 flex gap-2">
            <select
              className="field flex-1"
              value={addStudentId}
              onChange={(e) => setAddStudentId(e.target.value)}
            >
              <option value="">Выбрать ученика…</option>
              {students
                .filter((s) => !course.student_ids.includes(s.id))
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name || s.email}
                  </option>
                ))}
            </select>
            <button className="btn btn-primary !py-2 text-sm" onClick={() => void addStudent()}>
              Добавить
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
