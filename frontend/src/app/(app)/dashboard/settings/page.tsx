"use client";

import { useEffect, useRef, useState } from "react";

import { API_BASE, get, put, tokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Category, TutorDetail } from "@/lib/types";


type Profile = {
  full_name: string | null;
  avatar_url: string | null;
  experience_years: number | null;
  bio_short: string | null;
  bio_full: string | null;
  languages: string;
  category_ids: string[];
};

const EMPTY_PROFILE: Profile = {
  full_name: "",
  avatar_url: "",
  experience_years: null,
  bio_short: "",
  bio_full: "",
  languages: "",
  category_ids: [],
};

export default function SettingsPage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [categories, setCategories] = useState<Category[]>([]);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notifPermission, setNotifPermission] = useState<NotificationPermission | "unsupported">(
    "unsupported",
  );
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const avatarFileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user) return;
    get<{ full_name: string | null; avatar_url: string | null }>("/users/me", true)
      .then((p) => setProfile((f) => ({ ...f, full_name: p.full_name, avatar_url: p.avatar_url ?? "" })))
      .catch(() => undefined);
    if (typeof Notification !== "undefined") setNotifPermission(Notification.permission);
    if (user.role === "tutor") {
      get<Category[]>("/courses/categories")
        .then(setCategories)
        .catch(() => undefined);
      // Own tutor-specific fields aren't on GET /users/me (ProfileOut is the
      // shared shape used everywhere — batch lookups, chat peers, etc.) —
      // the public tutor detail route happens to have exactly this data.
      get<TutorDetail>(`/users/tutors/${user.id}`)
        .then((t) =>
          setProfile((f) => ({
            ...f,
            experience_years: t.experience_years,
            bio_short: t.bio_short ?? "",
            bio_full: t.bio_full ?? "",
            languages: (t.languages ?? []).join(", "),
            category_ids: t.category_ids ?? [],
          })),
        )
        .catch(() => undefined);
    }
  }, [user]);

  async function save() {
    setBusy(true);
    const payload: Record<string, unknown> = {
      full_name: profile.full_name,
      avatar_url: profile.avatar_url || null,
    };
    if (user?.role === "tutor") {
      payload.experience_years = profile.experience_years;
      payload.bio_short = profile.bio_short || null;
      payload.bio_full = profile.bio_full || null;
      payload.languages = profile.languages
        .split(",")
        .map((l) => l.trim())
        .filter(Boolean);
      payload.category_ids = profile.category_ids;
    }
    await put("/users/me", payload, true).catch(() => undefined);
    setBusy(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function uploadAvatar(file: File) {
    setUploadingAvatar(true);
    setAvatarError(null);
    try {
      const form = new FormData();
      form.append("bucket", "avatars");
      form.append("file", file);
      const token = tokens.access();
      const res = await fetch(`${API_BASE}/storage/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: form,
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail || "Не удалось загрузить фото");
      }
      const { url } = (await res.json()) as { url: string };
      const avatarUrl = `${API_BASE}${url}`;
      setProfile((p) => ({ ...p, avatar_url: avatarUrl }));
      await put("/users/me", { avatar_url: avatarUrl }, true);
    } catch (e) {
      setAvatarError(e instanceof Error ? e.message : "Не удалось загрузить фото");
    } finally {
      setUploadingAvatar(false);
      if (avatarFileRef.current) avatarFileRef.current.value = "";
    }
  }

  function toggleCategory(id: string) {
    setProfile((p) => ({
      ...p,
      category_ids: p.category_ids.includes(id)
        ? p.category_ids.filter((c) => c !== id)
        : [...p.category_ids, id],
    }));
  }

  async function enableNotifications() {
    if (typeof Notification === "undefined") return;
    const permission = await Notification.requestPermission();
    setNotifPermission(permission);
    if (permission === "granted") {
      new Notification("EduBridge", { body: "Уведомления включены — вы будете видеть их, даже свернув вкладку." });
    }
  }

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">
          Настройки
        </p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Профиль</h1>
      </header>

      <div className="card mt-8 space-y-4 p-6">
        <div>
          <label className="label">Имя</label>
          <input
            className="field"
            value={profile.full_name ?? ""}
            onChange={(e) => setProfile((p) => ({ ...p, full_name: e.target.value }))}
          />
        </div>

        <div>
          <label className="label">Фото</label>
          <div className="flex items-center gap-3">
            {profile.avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={profile.avatar_url}
                alt=""
                className="h-12 w-12 shrink-0 rounded-full object-cover"
                onError={(e) => (e.currentTarget.style.visibility = "hidden")}
              />
            ) : (
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-aurora-100 text-xs font-semibold text-aurora-700">
                {(profile.full_name || "EB").slice(0, 2).toUpperCase()}
              </span>
            )}
            <input
              ref={avatarFileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && void uploadAvatar(e.target.files[0])}
            />
            <button
              type="button"
              className="btn btn-ghost !py-2 text-sm"
              disabled={uploadingAvatar}
              onClick={() => avatarFileRef.current?.click()}
            >
              {uploadingAvatar ? "Загружаем…" : "Загрузить фото"}
            </button>
          </div>
          <input
            className="field mt-2"
            placeholder="…или вставьте ссылку на изображение"
            value={profile.avatar_url ?? ""}
            onChange={(e) => setProfile((p) => ({ ...p, avatar_url: e.target.value }))}
          />
          {avatarError && <p className="mt-1 text-xs text-coral-500">{avatarError}</p>}
          <p className="mt-1 text-xs text-ink-3">JPEG/PNG/WEBP/GIF, до 5 МБ.</p>
        </div>

        {user.role === "tutor" && (
          <>
            <div className="border-t border-line pt-4">
              <p className="text-sm font-semibold text-ink-2">Публичная анкета репетитора</p>
              <p className="mt-1 text-xs text-ink-3">
                Показывается на публичной странице{" "}
                <a href="/tutors" target="_blank" rel="noopener noreferrer" className="text-aurora-700 underline">
                  «Репетиторы»
                </a>
                .
              </p>
            </div>
            <div>
              <label className="label">Опыт работы (лет)</label>
              <input
                className="field max-w-32"
                type="number"
                min={0}
                max={80}
                value={profile.experience_years ?? ""}
                onChange={(e) =>
                  setProfile((p) => ({
                    ...p,
                    experience_years: e.target.value === "" ? null : Number(e.target.value),
                  }))
                }
              />
            </div>
            <div>
              <label className="label">Короткое описание (до 280 символов)</label>
              <textarea
                className="field min-h-20 resize-y"
                maxLength={280}
                value={profile.bio_short ?? ""}
                onChange={(e) => setProfile((p) => ({ ...p, bio_short: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Полное описание (для страницы анкеты)</label>
              <textarea
                className="field min-h-32 resize-y"
                value={profile.bio_full ?? ""}
                onChange={(e) => setProfile((p) => ({ ...p, bio_full: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Языки (через запятую)</label>
              <input
                className="field"
                placeholder="Русский, English, Кыргызча"
                value={profile.languages}
                onChange={(e) => setProfile((p) => ({ ...p, languages: e.target.value }))}
              />
            </div>
            <div>
              <label className="label">Категории / предметы</label>
              {categories.length ? (
                <div className="mt-1 flex flex-wrap gap-2">
                  {categories.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      className={`chip ${profile.category_ids.includes(c.id) ? "border-aurora-600! bg-aurora-50 text-aurora-700" : ""}`}
                      onClick={() => toggleCategory(c.id)}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-xs text-ink-3">Категорий пока нет.</p>
              )}
            </div>
          </>
        )}

        <button className="btn btn-primary !py-2.5 text-sm" disabled={busy} onClick={() => void save()}>
          {saved ? "Сохранено ✓" : "Сохранить"}
        </button>
      </div>

      <div className="card mt-6 p-6">
        <h2 className="display text-lg">Уведомления</h2>
        <p className="mt-1 text-sm text-ink-3">
          Браузерные уведомления о новых сообщениях и занятиях, даже когда вкладка свёрнута.
        </p>
        {notifPermission === "granted" ? (
          <p className="mt-3 text-sm text-jade-700">✓ Уведомления включены</p>
        ) : notifPermission === "unsupported" ? (
          <p className="mt-3 text-sm text-ink-3">Браузер не поддерживает уведомления.</p>
        ) : (
          <button className="btn btn-ghost mt-3 !py-2 text-sm" onClick={() => void enableNotifications()}>
            {notifPermission === "denied" ? "Заблокировано в браузере" : "Включить уведомления"}
          </button>
        )}
      </div>

    </div>
  );
}
