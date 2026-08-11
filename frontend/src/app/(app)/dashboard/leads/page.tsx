"use client";

import { useCallback, useEffect, useState } from "react";

import { get, put } from "@/lib/api";
import type { Lead, LeadStatus } from "@/lib/types";

const STATUS_LABEL: Record<LeadStatus, string> = {
  new: "Новая",
  contacted: "В работе",
  closed: "Закрыта",
};

const STATUS_TONE: Record<LeadStatus, string> = {
  new: "!bg-citrus-100 !text-citrus-700",
  contacted: "!bg-aurora-50 !text-aurora-700",
  closed: "!bg-jade-100 !text-jade-700",
};

const FILTERS: { value: LeadStatus | "all"; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "new", label: "Новые" },
  { value: "contacted", label: "В работе" },
  { value: "closed", label: "Закрыты" },
];

const NEXT_STATUS: Record<LeadStatus, LeadStatus | null> = {
  new: "contacted",
  contacted: "closed",
  closed: null,
};

const NEXT_LABEL: Record<LeadStatus, string> = {
  new: "Взять в работу",
  contacted: "Закрыть",
  closed: "",
};

export default function LeadsPage() {
  const [filter, setFilter] = useState<LeadStatus | "all">("new");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async (status: LeadStatus | "all") => {
    const path = status === "all" ? "/leads" : `/leads?status=${status}`;
    const items = await get<Lead[]>(path, true).catch(() => [] as Lead[]);
    setLeads(items);
  }, []);

  useEffect(() => {
    void load(filter);
  }, [filter, load]);

  async function advance(lead: Lead) {
    const next = NEXT_STATUS[lead.status];
    if (!next) return;
    setBusyId(lead.id);
    await put(`/leads/${lead.id}/status`, { status: next }, true).catch(() => undefined);
    await load(filter);
    setBusyId(null);
  }

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Заявки</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Заявки с сайта</h1>
        <p className="mt-2 text-sm text-ink-3">
          Анкеты с публичной формы «Оставить заявку» — свяжитесь с человеком и заведите ему аккаунт.
        </p>
      </header>

      <div className="mt-6 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`chip ${filter === f.value ? "!border-aurora-600 !bg-aurora-50 !text-aurora-700" : ""}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <ul className="mt-6 space-y-3">
        {leads.map((lead) => (
          <li key={lead.id} className="card p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold">{lead.full_name}</p>
                <p className="text-xs text-ink-3">
                  {new Date(lead.created_at).toLocaleString("ru-RU")}
                </p>
              </div>
              <span className={`chip ${STATUS_TONE[lead.status]}`}>{STATUS_LABEL[lead.status]}</span>
            </div>

            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              {lead.subject && <span className="chip">{lead.subject}</span>}
              {lead.goal && <span className="chip">{lead.goal}</span>}
              {lead.date_of_birth && (
                <span className="chip">Д.р. {new Date(lead.date_of_birth).toLocaleDateString("ru-RU")}</span>
              )}
              {lead.study_place && <span className="chip">{lead.study_place}</span>}
              {lead.destination_country && <span className="chip">Переезд: {lead.destination_country}</span>}
            </div>

            <div className="mt-3 flex flex-wrap gap-4 text-sm">
              {lead.contact_phone && (
                <a href={`tel:${lead.contact_phone}`} className="font-semibold text-aurora-700">
                  {lead.contact_phone}
                </a>
              )}
              {lead.contact_email && (
                <a href={`mailto:${lead.contact_email}`} className="font-semibold text-aurora-700">
                  {lead.contact_email}
                </a>
              )}
            </div>

            {NEXT_STATUS[lead.status] && (
              <button
                className="btn btn-ghost mt-4 !py-1.5 text-xs"
                disabled={busyId === lead.id}
                onClick={() => void advance(lead)}
              >
                {NEXT_LABEL[lead.status]}
              </button>
            )}
          </li>
        ))}
        {leads.length === 0 && <p className="card p-6 text-sm text-ink-3">Заявок пока нет.</p>}
      </ul>
    </div>
  );
}
