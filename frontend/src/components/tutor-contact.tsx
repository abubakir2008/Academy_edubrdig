"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { TutorCard } from "@/lib/types";

/** Primary contact action on a tutor card/profile — adapts to who's looking:
 * a signed-in user can just message the tutor directly (existing chat, no
 * new infrastructure); an anonymous visitor is sent to the same public
 * intake form (`/onboarding`) used everywhere else on the site, tagged with
 * this tutor — one shared request pipeline into the admin panel instead of
 * a separate one per tutor. */
export function TutorContact({ tutor, className = "" }: { tutor: TutorCard; className?: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [messaging, setMessaging] = useState(false);

  async function writeMessage() {
    setMessaging(true);
    try {
      await post("/chat/conversations", { peer_id: tutor.user_id }, true);
      router.push(`/dashboard/messages?peer=${tutor.user_id}`);
    } catch {
      setMessaging(false);
    }
  }

  if (user) {
    return (
      <button
        className={`btn btn-primary ${className}`}
        disabled={messaging}
        onClick={() => void writeMessage()}
      >
        {messaging ? "Открываем…" : "Написать сообщение"}
      </button>
    );
  }

  const params = new URLSearchParams({ tutor: tutor.user_id });
  if (tutor.full_name) params.set("name", tutor.full_name);

  return (
    <Link href={`/onboarding?${params.toString()}`} className={`btn btn-primary ${className}`}>
      Оставить заявку
    </Link>
  );
}
