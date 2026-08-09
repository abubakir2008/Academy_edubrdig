"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { del, get, put } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ZoomStatus } from "@/lib/types";


type Profile = {
  full_name: string | null;
  country: string | null;
  bio: string | null;
  phone: string | null;
};

export default function SettingsPage() {
  const { user } = useAuth();
  const params = useSearchParams();
  const zoomRedirect = params.get("zoom"); // "connected" | "error" | null
  const [profile, setProfile] = useState<Profile>({ full_name: "", country: "", bio: "", phone: "" });
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notifPermission, setNotifPermission] = useState<NotificationPermission | "unsupported">(
    "unsupported",
  );
  const [zoomStatus, setZoomStatus] = useState<ZoomStatus | null>(null);
  const [zoomBusy, setZoomBusy] = useState(false);

  const loadZoomStatus = useCallback(async () => {
    const status = await get<ZoomStatus>("/calendar/zoom/status", true).catch(() => null);
    setZoomStatus(status);
  }, []);

  useEffect(() => {
    if (!user) return;
    get<Profile>("/users/me", true)
      .then(setProfile)
      .catch(() => undefined);
    if (typeof Notification !== "undefined") setNotifPermission(Notification.permission);
    if (user.role === "tutor") void loadZoomStatus();
  }, [user, loadZoomStatus]);

  async function connectZoom() {
    setZoomBusy(true);
    try {
      const { authorize_url } = await get<{ authorize_url: string }>("/calendar/zoom/connect", true);
      window.location.href = authorize_url;
    } catch {
      setZoomBusy(false);
    }
  }

  async function disconnectZoom() {
    setZoomBusy(true);
    await del("/calendar/zoom").catch(() => undefined);
    await loadZoomStatus();
    setZoomBusy(false);
  }

  async function save() {
    setBusy(true);
    await put("/users/me", profile, true).catch(() => undefined);
    setBusy(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
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

      {zoomRedirect === "connected" && (
        <p className="mt-4 rounded-xl bg-jade-100 px-4 py-3 text-sm text-jade-700">
          Zoom подключён.
        </p>
      )}
      {zoomRedirect === "error" && (
        <p className="mt-4 rounded-xl bg-coral-100 px-4 py-3 text-sm text-coral-500">
          Не удалось подключить Zoom. Попробуйте ещё раз.
        </p>
      )}

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
          <label className="label">Страна (код, напр. KG)</label>
          <input
            className="field"
            maxLength={2}
            value={profile.country ?? ""}
            onChange={(e) => setProfile((p) => ({ ...p, country: e.target.value.toUpperCase() }))}
          />
        </div>
        <div>
          <label className="label">Телефон</label>
          <input
            className="field"
            value={profile.phone ?? ""}
            onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))}
          />
        </div>
        <div>
          <label className="label">О себе</label>
          <textarea
            className="field min-h-24 resize-y"
            value={profile.bio ?? ""}
            onChange={(e) => setProfile((p) => ({ ...p, bio: e.target.value }))}
          />
        </div>
        <button className="btn btn-primary !py-2.5 text-sm" disabled={busy} onClick={() => void save()}>
          {saved ? "Сохранено ✓" : "Сохранить"}
        </button>
      </div>

      <div className="card mt-6 p-6">
        <h2 className="display text-lg">Уведомления</h2>
        <p className="mt-1 text-sm text-ink-3">
          Браузерные уведомления о новых сообщениях и бронированиях, даже когда вкладка свёрнута.
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

      {user.role === "tutor" && (
        <div className="card mt-6 p-6">
          <h2 className="display text-lg">Zoom</h2>
          <p className="mt-1 text-sm text-ink-3">
            Свой Zoom-аккаунт для видеоуроков — конференция создаётся автоматически при
            добавлении урока в расписание курса.
          </p>
          {zoomStatus?.connected ? (
            <>
              <p className="mt-3 text-sm text-jade-700">
                ✓ Подключено{zoomStatus.email ? ` как ${zoomStatus.email}` : ""}
              </p>
              <button
                className="btn btn-ghost mt-3 !py-2 text-sm"
                disabled={zoomBusy}
                onClick={() => void disconnectZoom()}
              >
                Отключить
              </button>
            </>
          ) : (
            <button
              className="btn btn-primary mt-3 !py-2 text-sm"
              disabled={zoomBusy}
              onClick={() => void connectZoom()}
            >
              Подключить Zoom
            </button>
          )}
        </div>
      )}

    </div>
  );
}
