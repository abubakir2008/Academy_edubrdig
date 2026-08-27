"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { MessageSquare } from "lucide-react";

import { Avatar } from "@/components/avatar";
import { del, get, post, put } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AdminUser, Category, CourseDetail, Profile } from "@/lib/types";

export default function CourseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [tutors, setTutors] = useState<AdminUser[]>([]);
  const [students, setStudents] = useState<AdminUser[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [titleDraft, setTitleDraft] = useState("");
  const [descriptionDraft, setDescriptionDraft] = useState("");
  const [categoryDraft, setCategoryDraft] = useState("");
  const [addStudentId, setAddStudentId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [messaging, setMessaging] = useState<string | null>(null);
  const [resolvedProfiles, setResolvedProfiles] = useState<Record<string, Profile>>({});

  const isSuperAdmin = user?.role === "super_admin";
  // A tutor can message their own roster; staff can message anyone's.
  const canMessage = isSuperAdmin || (user?.role === "tutor" && user.id === course?.teacher_id);

  const load = useCallback(async () => {
    const c = await get<CourseDetail>(`/courses/${id}`, true).catch(() => null);
    if (!c) {
      setNotFound(true);
      return;
    }
    setCourse(c);
    setTitleDraft(c.title);
    setDescriptionDraft(c.description ?? "");
    setCategoryDraft(c.category_id ?? "");
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!isSuperAdmin) return;
    get<AdminUser[]>("/auth/admin/users?role=tutor", true).then(setTutors).catch(() => undefined);
    get<AdminUser[]>("/auth/admin/users?role=student", true).then(setStudents).catch(() => undefined);
  }, [isSuperAdmin]);

  useEffect(() => {
    get<Category[]>("/courses/categories")
      .then(setCategories)
      .catch(() => undefined);
  }, []);

  // `/auth/admin/users` above is staff-only, so a tutor viewing their own
  // course would otherwise see raw ids with no photo — resolve name + avatar
  // for everyone not already covered via one batched round trip.
  useEffect(() => {
    if (!course) return;
    const ids = Array.from(
      new Set(
        [course.teacher_id, ...course.student_ids].filter(
          (uid): uid is string => Boolean(uid) && !(uid! in resolvedProfiles),
        ),
      ),
    );
    if (ids.length === 0) return;
    get<Profile[]>(`/users/batch?ids=${encodeURIComponent(ids.join(","))}`)
      .then((profiles) => {
        setResolvedProfiles((prev) => {
          const next = { ...prev };
          for (const p of profiles) next[p.user_id] = p;
          return next;
        });
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course]);

  async function saveDetails() {
    setError(null);
    try {
      await put(
        `/courses/${id}`,
        { title: titleDraft, description: descriptionDraft || null, category_id: categoryDraft || null },
        true,
      );
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
    setError(null);
    try {
      await del(`/courses/${id}/students/${studentId}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось убрать студента с курса");
    }
  }

  async function messageStudent(studentId: string) {
    setMessaging(studentId);
    try {
      await post("/chat/conversations", { peer_id: studentId }, true);
      router.push(`/dashboard/messages?peer=${studentId}`);
    } catch {
      setMessaging(null);
    }
  }

  function profileFor(userId: string, pool: AdminUser[]): { name: string; avatar: string | null } {
    const match = pool.find((u) => u.id === userId);
    const resolved = resolvedProfiles[userId];
    return {
      name: match?.full_name || match?.email || resolved?.full_name || "…",
      avatar: resolved?.avatar_url ?? null,
    };
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
            <select className="field" value={categoryDraft} onChange={(e) => setCategoryDraft(e.target.value)}>
              <option value="">Без категории</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            {error && <p className="text-sm text-coral-500">{error}</p>}
            <button className="btn btn-primary !py-2 text-sm" onClick={() => void saveDetails()}>
              Сохранить
            </button>
          </div>
        ) : (
          <>
            <p className="mt-2 text-sm text-ink-3">{course.description || "Без описания."}</p>
            {course.category_id && (
              <span className="chip mt-3 inline-block">
                {categories.find((c) => c.id === course.category_id)?.name ?? "…"}
              </span>
            )}
          </>
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
        ) : course.teacher_id ? (
          <div className="mt-3 flex items-center gap-3">
            <Avatar name={profileFor(course.teacher_id, tutors).name} url={profileFor(course.teacher_id, tutors).avatar} />
            <span className="text-sm text-ink-2">{profileFor(course.teacher_id, tutors).name}</span>
          </div>
        ) : (
          <p className="mt-2 text-sm text-ink-3">Не назначен</p>
        )}
      </section>

      <section className="card mt-8 p-6">
        <h2 className="display text-lg">Ученики ({course.student_ids.length})</h2>
        <ul className="mt-3 space-y-2">
          {course.student_ids.map((sid) => (
            <li key={sid} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex min-w-0 items-center gap-3">
                <Avatar name={profileFor(sid, students).name} url={profileFor(sid, students).avatar} size="sm" />
                <span className="truncate">{profileFor(sid, students).name}</span>
              </span>
              <span className="flex shrink-0 items-center gap-3">
                {canMessage && (
                  <button
                    className="flex items-center gap-1.5 text-xs font-semibold text-aurora-700 disabled:opacity-50"
                    disabled={messaging === sid}
                    onClick={() => void messageStudent(sid)}
                    title="Написать"
                  >
                    <MessageSquare className="h-3.5 w-3.5" aria-hidden />
                    Написать
                  </button>
                )}
                {isSuperAdmin && (
                  <button className="text-xs font-semibold text-coral-500" onClick={() => void removeStudent(sid)}>
                    Убрать
                  </button>
                )}
              </span>
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
