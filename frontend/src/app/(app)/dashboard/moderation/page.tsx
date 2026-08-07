"use client";

import { useCallback, useEffect, useState } from "react";

import { get, post } from "@/lib/api";
import type { Complaint, Document, VerificationRequest } from "@/lib/types";

const DOC_TYPE_LABEL: Record<string, string> = {
  certificate: "Сертификат / диплом",
  identity: "Документ, удостоверяющий личность",
};

export default function ModerationPage() {
  const [requests, setRequests] = useState<VerificationRequest[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [reqs, docs, comp] = await Promise.all([
      get<VerificationRequest[]>("/moderation/verification?status=pending", true).catch(
        () => [] as VerificationRequest[],
      ),
      get<Document[]>("/moderation/documents?status=pending", true).catch(() => [] as Document[]),
      get<Complaint[]>("/reviews/complaints?status=open", true).catch(() => [] as Complaint[]),
    ]);
    setRequests(reqs);
    setDocuments(docs);
    setComplaints(comp);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function review(id: string, approve: boolean) {
    setBusy(id);
    await post(`/moderation/verification/${id}/review`, { approve }, true).catch(() => undefined);
    await load();
    setBusy(null);
  }

  async function reviewDocument(id: string, approve: boolean) {
    setBusy(id);
    await post(`/moderation/documents/${id}/review`, { approve }, true).catch(() => undefined);
    await load();
    setBusy(null);
  }

  async function resolveComplaint(id: string, status: "resolved" | "dismissed") {
    setBusy(id);
    await post(`/reviews/complaints/${id}/resolve`, { status }, true).catch(() => undefined);
    await load();
    setBusy(null);
  }

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">
          Модерация
        </p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Очередь</h1>
      </header>

      <section className="mt-8">
        <h2 className="display text-lg">Заявки на верификацию ({requests.length})</h2>
        {requests.length ? (
          <ul className="mt-4 space-y-3">
            {requests.map((r) => (
              <li key={r.id} className="card flex flex-wrap items-center justify-between gap-3 p-5">
                <div>
                  <p className="font-semibold">Репетитор {r.tutor_id.slice(0, 8)}</p>
                  <p className="mt-1 text-sm text-ink-3">Тип: {r.kind}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    className="btn btn-primary !py-2 text-sm"
                    disabled={busy === r.id}
                    onClick={() => void review(r.id, true)}
                  >
                    Одобрить
                  </button>
                  <button
                    className="btn btn-ghost !py-2 text-sm"
                    disabled={busy === r.id}
                    onClick={() => void review(r.id, false)}
                  >
                    Отклонить
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="card mt-4 p-6 text-sm text-ink-3">Очередь пуста.</p>
        )}
      </section>

      <section className="mt-8">
        <h2 className="display text-lg">Документы на проверку ({documents.length})</h2>
        {documents.length ? (
          <ul className="mt-4 space-y-3">
            {documents.map((d) => (
              <li key={d.id} className="card flex flex-wrap items-center justify-between gap-3 p-5">
                <div>
                  <p className="font-semibold">Репетитор {d.tutor_id.slice(0, 8)}</p>
                  <p className="mt-1 text-sm text-ink-3">
                    {DOC_TYPE_LABEL[d.doc_type] ?? d.doc_type} ·{" "}
                    <a href={d.file_url} target="_blank" rel="noreferrer" className="font-semibold text-aurora-700">
                      Открыть файл
                    </a>
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    className="btn btn-primary !py-2 text-sm"
                    disabled={busy === d.id}
                    onClick={() => void reviewDocument(d.id, true)}
                  >
                    Одобрить
                  </button>
                  <button
                    className="btn btn-ghost !py-2 text-sm"
                    disabled={busy === d.id}
                    onClick={() => void reviewDocument(d.id, false)}
                  >
                    Отклонить
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="card mt-4 p-6 text-sm text-ink-3">Документов на проверке нет.</p>
        )}
      </section>

      <section className="mt-8">
        <h2 className="display text-lg">Жалобы ({complaints.length})</h2>
        {complaints.length ? (
          <ul className="mt-4 space-y-3">
            {complaints.map((c) => (
              <li key={c.id} className="card p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold">
                      На {c.target_type === "tutor" ? "репетитора" : "отзыв"} {c.target_id.slice(0, 8)}
                    </p>
                    <p className="mt-1 text-sm text-ink-3">{c.reason}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      className="btn btn-primary !py-2 text-sm"
                      disabled={busy === c.id}
                      onClick={() => void resolveComplaint(c.id, "resolved")}
                    >
                      Решено
                    </button>
                    <button
                      className="btn btn-ghost !py-2 text-sm"
                      disabled={busy === c.id}
                      onClick={() => void resolveComplaint(c.id, "dismissed")}
                    >
                      Отклонить
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="card mt-4 p-6 text-sm text-ink-3">Жалоб нет.</p>
        )}
      </section>
    </div>
  );
}
