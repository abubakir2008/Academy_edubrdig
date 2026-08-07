"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { get, post } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { VerificationRequest } from "@/lib/types";

const STATUS: Record<string, { label: string; tone: string }> = {
  pending: { label: "На рассмотрении", tone: "!bg-citrus-100 !text-citrus-700" },
  approved: { label: "Одобрено", tone: "!bg-jade-100 !text-jade-700" },
  rejected: { label: "Отклонено", tone: "!bg-coral-100 !text-coral-500" },
};

export default function VerificationPage() {
  const { user } = useAuth();
  const [requests, setRequests] = useState<VerificationRequest[]>([]);
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    if (!user || user.role !== "tutor") return;
    const items = await get<VerificationRequest[]>("/moderation/verification/me", true).catch(
      () => [] as VerificationRequest[],
    );
    setRequests(items);
  }, [user]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submitProfile() {
    setBusy(true);
    setError(null);
    try {
      await post("/moderation/verification", { kind: "profile" }, true);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отправить заявку");
    } finally {
      setBusy(false);
    }
  }

  async function uploadDoc(file: File) {
    setBusy(true);
    setError(null);
    try {
      const presign = await post<{ upload_url: string; bucket: string; object_name: string }>(
        "/storage/presign-upload",
        { bucket: "certificates", filename: file.name },
        true,
      );
      await fetch(presign.upload_url, { method: "PUT", body: file });
      const download = await post<{ download_url: string }>(
        "/storage/presign-download",
        { bucket: presign.bucket, object_name: presign.object_name },
        true,
      );
      await post("/moderation/documents", { doc_type: "certificate", file_url: download.download_url }, true);
      setUploadedDocs((prev) => [...prev, file.name]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить документ (нужен профиль хранилища MinIO)");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  if (user && user.role !== "tutor") {
    return (
      <div className="mx-auto max-w-2xl px-5 py-12 text-sm text-ink-3">
        Верификация доступна только для репетиторов.
      </div>
    );
  }

  const pendingOrLatest = requests[0];
  const canSubmit = !pendingOrLatest || pendingOrLatest.status === "rejected";

  return (
    <div className="mx-auto max-w-2xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">
          Верификация
        </p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Подтвердите профиль</h1>
        <p className="mt-2 text-sm text-ink-3">
          Проверенный профиль получает значок доверия и выше в выдаче поиска. Модератор
          рассматривает заявки вручную.
        </p>
      </header>

      {error && <p className="card mt-6 border-coral-500/40 bg-coral-100 p-4 text-sm">{error}</p>}

      <div className="card mt-6 p-6">
        <h2 className="display text-lg">1. Заявка на проверку профиля</h2>
        {requests.length > 0 && (
          <ul className="mt-3 space-y-2">
            {requests.map((r) => {
              const s = STATUS[r.status] ?? { label: r.status, tone: "" };
              return (
                <li key={r.id} className="flex items-center justify-between text-sm">
                  <span className="text-ink-3">{r.kind === "profile" ? "Профиль" : "Личность"}</span>
                  <span className={`chip ${s.tone}`}>{s.label}</span>
                </li>
              );
            })}
          </ul>
        )}
        {canSubmit && (
          <button
            className="btn btn-primary mt-4 !py-2.5 text-sm"
            disabled={busy}
            onClick={() => void submitProfile()}
          >
            {requests.length > 0 ? "Отправить повторно" : "Отправить на проверку"}
          </button>
        )}
      </div>

      <div className="card mt-6 p-6">
        <h2 className="display text-lg">2. Документы (диплом, сертификаты)</h2>
        <p className="mt-1 text-sm text-ink-3">Необязательно, но ускоряет одобрение.</p>
        <input
          ref={fileRef}
          type="file"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && void uploadDoc(e.target.files[0])}
        />
        <button className="btn btn-ghost mt-3 !py-2.5 text-sm" disabled={busy} onClick={() => fileRef.current?.click()}>
          {busy ? "Загружаем…" : "Загрузить документ"}
        </button>
        {uploadedDocs.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm text-ink-3">
            {uploadedDocs.map((name, i) => (
              <li key={i}>✓ {name}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
