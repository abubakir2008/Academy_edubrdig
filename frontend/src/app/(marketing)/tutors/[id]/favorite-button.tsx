"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { del, get, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Favorite } from "@/lib/types";

export function FavoriteButton({ tutorId }: { tutorId: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [active, setActive] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    get<Favorite[]>("/students/me/favorites", true)
      .then((list) => setActive(list.some((f) => f.tutor_id === tutorId)))
      .catch(() => undefined);
  }, [user, tutorId]);

  async function toggle() {
    if (!user) {
      router.push(`/login?next=/tutors/${tutorId}`);
      return;
    }
    setBusy(true);
    const next = !active;
    setActive(next); // optimistic — reverted below if the call fails
    try {
      if (next) await post(`/students/me/favorites/${tutorId}`, undefined, true);
      else await del(`/students/me/favorites/${tutorId}`);
    } catch {
      setActive(!next);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={() => void toggle()}
      disabled={busy}
      aria-pressed={active}
      aria-label={active ? "Убрать из избранного" : "В избранное"}
      title={active ? "Убрать из избранного" : "В избранное"}
      className={`flex h-11 w-11 items-center justify-center rounded-full border transition-colors ${
        active
          ? "border-coral-500 bg-coral-100 text-coral-500"
          : "border-line text-ink-3 hover:border-ink hover:text-ink"
      }`}
    >
      <svg width="20" height="20" viewBox="0 0 20 20" fill={active ? "currentColor" : "none"} aria-hidden>
        <path
          d="M10 16.5S3 12.4 3 7.9A3.9 3.9 0 0110 5.6a3.9 3.9 0 017 2.3c0 4.5-7 8.6-7 8.6z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}
