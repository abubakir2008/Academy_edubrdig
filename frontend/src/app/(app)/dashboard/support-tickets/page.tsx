"use client";

import { useCallback, useEffect, useState } from "react";

import { get, post } from "@/lib/api";
import type { Ticket, TicketMessage } from "@/lib/types";

const STATUS_TONE: Record<string, string> = {
  open: "!bg-citrus-100 !text-citrus-700",
  pending: "!bg-aurora-50 !text-aurora-700",
  closed: "!bg-jade-100 !text-jade-700",
};

export default function SupportTicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<TicketMessage[]>([]);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);

  const loadTickets = useCallback(async () => {
    const items = await get<Ticket[]>("/support/tickets", true).catch(() => [] as Ticket[]);
    setTickets(items);
  }, []);

  useEffect(() => {
    void loadTickets();
  }, [loadTickets]);

  const loadMessages = useCallback(async (id: string) => {
    const items = await get<TicketMessage[]>(`/support/tickets/${id}/messages`, true).catch(
      () => [] as TicketMessage[],
    );
    setMessages(items);
  }, []);

  useEffect(() => {
    if (activeId) void loadMessages(activeId);
  }, [activeId, loadMessages]);

  const active = tickets.find((t) => t.id === activeId);

  async function sendReply() {
    if (!activeId || !reply.trim()) return;
    setBusy(true);
    await post(`/support/tickets/${activeId}/messages`, { text: reply }, true).catch(() => undefined);
    setReply("");
    await Promise.all([loadMessages(activeId), loadTickets()]);
    setBusy(false);
  }

  async function closeTicket() {
    if (!activeId) return;
    setBusy(true);
    await post(`/support/tickets/${activeId}/close`, undefined, true).catch(() => undefined);
    await loadTickets();
    setBusy(false);
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-5xl lg:h-screen">
      <aside className="w-72 shrink-0 overflow-y-auto border-r border-line px-3 py-6">
        <p className="px-2 text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">
          Тикеты
        </p>
        <ul className="mt-4 space-y-1">
          {tickets.map((t) => (
            <li key={t.id}>
              <button
                onClick={() => setActiveId(t.id)}
                className={`w-full rounded-xl px-3 py-2.5 text-left text-sm ${
                  t.id === activeId ? "bg-aurora-50 text-aurora-700" : "hover:bg-paper-2"
                }`}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{t.subject}</span>
                  <span className={`chip shrink-0 text-xs ${STATUS_TONE[t.status] ?? ""}`}>{t.status}</span>
                </span>
              </button>
            </li>
          ))}
          {tickets.length === 0 && <p className="px-2 py-4 text-sm text-ink-3">Тикетов нет.</p>}
        </ul>
      </aside>

      <section className="flex flex-1 flex-col">
        {active ? (
          <>
            <header className="flex items-center justify-between border-b border-line px-6 py-4">
              <div>
                <p className="font-semibold">{active.subject}</p>
                <p className="text-xs text-ink-3">
                  Пользователь {active.user_id.slice(0, 8)} · приоритет {active.priority}
                </p>
              </div>
              {active.status !== "closed" && (
                <button className="btn btn-ghost !py-2 text-sm" onClick={() => void closeTicket()}>
                  Закрыть
                </button>
              )}
            </header>

            <div className="flex-1 overflow-y-auto px-6 py-4">
              <ul className="space-y-3">
                {messages.map((m) => (
                  <li key={m.id} className={`flex ${m.is_staff ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[70%] rounded-2xl px-4 py-2.5 text-sm ${m.is_staff ? "bg-aurora-600 text-white" : "bg-paper-2"}`}>
                      {m.text}
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {active.status !== "closed" && (
              <div className="flex items-center gap-2 border-t border-line px-6 py-4">
                <input
                  className="field flex-1"
                  placeholder="Ответ…"
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && void sendReply()}
                />
                <button className="btn btn-primary !px-5" disabled={busy} onClick={() => void sendReply()}>
                  Отправить
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-ink-3">
            Выберите тикет слева
          </div>
        )}
      </section>
    </div>
  );
}
