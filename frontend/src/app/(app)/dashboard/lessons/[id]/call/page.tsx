"use client";

import "@livekit/components-styles";

import { LiveKitRoom, VideoConference } from "@livekit/components-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, get } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatBishkekDateTime } from "@/lib/time";
import type { Lesson, LessonJoin } from "@/lib/types";

/**
 * The lesson's video call, embedded in the dashboard instead of redirecting
 * out to a third-party app the way the old Zoom join link did. `join`
 * mints a fresh LiveKit token server-side on every visit — see
 * calendar's `GET /lessons/{id}/join` — so there's nothing to persist here
 * beyond the lesson id in the URL.
 */
export default function LessonCallPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [join, setJoin] = useState<LessonJoin | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    async function load() {
      try {
        const name = encodeURIComponent(user!.full_name || user!.email);
        const [lessonData, joinData] = await Promise.all([
          get<Lesson>(`/calendar/lessons/${id}`, true),
          get<LessonJoin>(`/calendar/lessons/${id}/join?name=${name}`, true),
        ]);
        if (cancelled) return;
        setLesson(lessonData);
        setJoin(joinData);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : "Не удалось подключиться к уроку");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [id, user]);

  if (!user) return null;

  return (
    <div className="mx-auto max-w-5xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Урок</p>
          <h1 className="display mt-2 text-[clamp(1.5rem,3vw,2.25rem)]">
            {lesson?.title || "Видеозанятие"}
          </h1>
          {lesson && (
            <p className="mt-1 text-sm text-ink-3">
              {formatBishkekDateTime(lesson.scheduled_start)} (время Бишкека)
            </p>
          )}
        </div>
        {lesson && (
          <Link href={`/dashboard/courses/${lesson.course_id}/calendar`} className="btn btn-ghost">
            ← К курсу
          </Link>
        )}
      </header>

      {error && (
        <div className="card mt-8 p-6 text-sm text-coral-500">
          {error}
          {error.toLowerCase().includes("livekit") && (
            <p className="mt-2 text-ink-3">
              Видеосвязь ещё не настроена на сервере — обратитесь к администратору платформы.
            </p>
          )}
        </div>
      )}

      {!error && !join && <div className="card mt-8 p-6 text-sm text-ink-3">Подключаемся…</div>}

      {join && (
        <div className="mt-8 h-[75vh] overflow-hidden rounded-2xl border border-line" data-lk-theme="default">
          <LiveKitRoom
            serverUrl={join.livekit_url}
            token={join.token}
            connect
            video
            audio
            style={{ height: "100%" }}
            onDisconnected={() => router.push(lesson ? `/dashboard/courses/${lesson.course_id}/calendar` : "/dashboard")}
          >
            <VideoConference />
          </LiveKitRoom>
        </div>
      )}
    </div>
  );
}
