"use client";

import "@livekit/components-styles";

import { LiveKitRoom, VideoConference } from "@livekit/components-react";
import { PictureInPicture2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { ApiError, get } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatBishkekDateTime } from "@/lib/time";
import type { Lesson, LessonJoin } from "@/lib/types";

declare global {
  interface Window {
    documentPictureInPicture?: {
      requestWindow: (options?: { width?: number; height?: number }) => Promise<Window>;
      window: Window | null;
    };
  }
}

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

  // The call always portals into `portalTarget` — either this in-page div or
  // a container living inside the floating window — so toggling the popup
  // never unmounts <LiveKitRoom>, just moves where its output renders. An
  // unmount there would mean a real disconnect/reconnect, visible to the
  // other participant as "X left the call" / "X joined".
  const mainContainerRef = useRef<HTMLDivElement>(null);
  const [, forceRerender] = useState(0);
  const [pipWindow, setPipWindow] = useState<Window | null>(null);
  const [pipContainer, setPipContainer] = useState<HTMLDivElement | null>(null);
  const pipSupported = typeof window !== "undefined" && "documentPictureInPicture" in window;

  useEffect(() => {
    forceRerender((n) => n + 1); // mainContainerRef.current wasn't attached yet on the first render
  }, []);

  useEffect(() => {
    // Closing the tab/navigating away with the popup still open shouldn't
    // leave an orphaned floating window showing a frozen last frame.
    return () => {
      pipWindow?.close();
    };
  }, [pipWindow]);

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

  async function openFloatingWindow() {
    if (!window.documentPictureInPicture) return;
    const pipWin = await window.documentPictureInPicture.requestWindow({ width: 420, height: 320 });

    // A Document PiP window starts with a blank document — none of the main
    // page's stylesheets carry over automatically, so both Tailwind's
    // output and LiveKit's own component styles have to be copied by hand
    // or the popped-out call renders unstyled.
    for (const sheet of Array.from(document.styleSheets)) {
      try {
        if (sheet.href) {
          const link = pipWin.document.createElement("link");
          link.rel = "stylesheet";
          link.href = sheet.href;
          pipWin.document.head.appendChild(link);
        } else {
          const style = pipWin.document.createElement("style");
          style.textContent = Array.from(sheet.cssRules)
            .map((rule) => rule.cssText)
            .join("\n");
          pipWin.document.head.appendChild(style);
        }
      } catch {
        // Cross-origin stylesheet — can't read its rules, nothing to copy.
      }
    }
    pipWin.document.body.style.margin = "0";
    pipWin.document.body.style.background = "#000";
    pipWin.document.body.setAttribute("data-lk-theme", "default");
    const container = pipWin.document.createElement("div");
    container.style.height = "100vh";
    pipWin.document.body.appendChild(container);

    pipWin.addEventListener(
      "pagehide",
      () => {
        setPipWindow(null);
        setPipContainer(null);
      },
      { once: true },
    );

    setPipWindow(pipWin);
    setPipContainer(container);
  }

  if (!user) return null;

  const portalTarget = pipContainer ?? mainContainerRef.current;

  return (
    <div className="mx-auto max-w-5xl px-3 py-4 sm:px-5 sm:py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-3 sm:gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Урок</p>
          <h1 className="display mt-2 text-[clamp(1.35rem,4vw,2.25rem)]">
            {lesson?.title || "Видеозанятие"}
          </h1>
          {lesson && (
            <p className="mt-1 text-sm text-ink-3">
              {formatBishkekDateTime(lesson.scheduled_start)} (время Бишкека)
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {join && pipSupported && !pipWindow && (
            <button type="button" className="btn btn-ghost" onClick={() => void openFloatingWindow()}>
              <PictureInPicture2 className="h-4 w-4" aria-hidden /> Всплывающее окно
            </button>
          )}
          {lesson && (
            <Link href={`/dashboard/courses/${lesson.course_id}/calendar`} className="btn btn-ghost">
              ← К курсу
            </Link>
          )}
        </div>
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
        <div
          ref={mainContainerRef}
          className="mt-4 h-[calc(100dvh-260px)] min-h-[360px] overflow-hidden rounded-2xl border border-line sm:mt-8 sm:h-[75vh]"
          data-lk-theme="default"
        >
          {pipWindow && (
            <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center text-sm text-ink-3">
              <PictureInPicture2 className="h-8 w-8" aria-hidden />
              <p>Звонок открыт в отдельном плавающем окне.</p>
              <button type="button" className="btn btn-ghost" onClick={() => pipWindow.close()}>
                Вернуть на страницу
              </button>
            </div>
          )}
          {portalTarget &&
            createPortal(
              <LiveKitRoom
                serverUrl={join.livekit_url}
                token={join.token}
                connect
                video
                // Explicit rather than relying on the SDK's implicit defaults —
                // these are what actually suppress a participant hearing their
                // own voice looped back through someone else's open mic.
                audio={{ echoCancellation: true, noiseSuppression: true, autoGainControl: true }}
                style={{ height: "100%" }}
                onDisconnected={() =>
                  router.push(lesson ? `/dashboard/courses/${lesson.course_id}/calendar` : "/dashboard")
                }
              >
                <VideoConference />
              </LiveKitRoom>,
              portalTarget,
            )}
        </div>
      )}
    </div>
  );
}
