"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { API_BASE, get, post, tokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";
import type { ChatMessage, Conversation } from "@/lib/types";

type Peer = { user_id: string; full_name: string | null };

export default function MessagesPage() {
  const { user } = useAuth();
  const params = useSearchParams();
  // Deep-link from e.g. a course roster's "Написать" button — open the
  // conversation with this peer instead of just the first one in the list.
  const targetPeer = params.get("peer");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [peerNames, setPeerNames] = useState<Record<string, string>>({});
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(async () => {
    const items = await get<Conversation[]>("/chat/conversations", true).catch(() => [] as Conversation[]);
    setConversations(items);
    const forPeer = targetPeer && items.find((c) => c.participants.includes(targetPeer));
    if (forPeer) setActiveId(forPeer.id);
    else if (!activeId && items.length) setActiveId(items[0].id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetPeer]);

  useEffect(() => {
    if (user) void loadConversations();
  }, [user, loadConversations]);

  // Chat only ever stores participant ids — resolve every peer's display
  // name once per conversation list load, via one batched GET /users/batch
  // instead of one GET /users/{id} per peer. That used to queue behind the
  // browser's per-origin connection cap (6 in Chrome/Firefox over HTTP/1.1)
  // once someone had more than a handful of conversations, stalling the
  // sidebar for seconds — measured ~145ms for 6 peers, growing linearly past
  // the cap; the batched call stays flat regardless of peer count.
  useEffect(() => {
    const peerIds = Array.from(
      new Set(
        conversations
          .map((c) => c.participants.find((p) => p !== user?.id))
          .filter((id): id is string => Boolean(id) && !(id! in peerNames)),
      ),
    );
    if (peerIds.length === 0) return;
    get<Peer[]>(`/users/batch?ids=${encodeURIComponent(peerIds.join(","))}`)
      .catch(() => [] as Peer[])
      .then((profiles) => {
        const byId = new Map(profiles.map((p) => [p.user_id, p.full_name]));
        setPeerNames((prev) => {
          const next = { ...prev };
          for (const id of peerIds) next[id] = byId.get(id) || "Без имени";
          return next;
        });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversations, user?.id]);

  const loadMessages = useCallback(async (cid: string) => {
    const items = await get<ChatMessage[]>(`/chat/conversations/${cid}/messages`, true).catch(
      () => [] as ChatMessage[],
    );
    setMessages(items);
    await post(`/chat/conversations/${cid}/read`, undefined, true).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!activeId) return;
    void loadMessages(activeId);

    wsRef.current?.close();
    const token = tokens.access();
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}${API_BASE}/chat/ws/${activeId}?token=${token}`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as ChatMessage;
      setMessages((prev) => [...prev, msg]);
    };
    wsRef.current = ws;
    return () => ws.close();
  }, [activeId, loadMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!activeId || !text.trim()) return;
    const body = text;
    setText("");
    await post(`/chat/conversations/${activeId}/messages`, { text: body }, true).catch(() => undefined);
  }

  async function sendFile(file: File) {
    if (!activeId) return;
    setUploading(true);
    try {
      const presign = await post<{ upload_url: string; bucket: string; object_name: string }>(
        "/storage/presign-upload",
        { bucket: "chat", filename: file.name },
        true,
      );
      await fetch(presign.upload_url, { method: "PUT", body: file });
      const download = await post<{ download_url: string }>(
        "/storage/presign-download",
        { bucket: presign.bucket, object_name: presign.object_name },
        true,
      );
      await post(
        `/chat/conversations/${activeId}/messages`,
        { text: `📎 ${file.name}`, attachment_url: download.download_url, attachment_name: file.name },
        true,
      );
    } catch {
      // Storage needs the "full" compose profile (MinIO) — silently no-op if
      // it isn't running rather than breaking the whole chat.
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  const active = conversations.find((c) => c.id === activeId);
  const peerId = active?.participants.find((p) => p !== user?.id);

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-5xl lg:h-screen">
      <aside className="w-64 shrink-0 overflow-y-auto border-r border-line px-3 py-6">
        <p className="px-2 text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">
          Сообщения
        </p>
        <ul className="mt-4 space-y-1">
          {conversations.map((c) => {
            const peerId = c.participants.find((p) => p !== user?.id) ?? "?";
            const peerName = peerNames[peerId] ?? "…";
            return (
              <li key={c.id}>
                <button
                  onClick={() => setActiveId(c.id)}
                  className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2.5 text-left text-sm ${
                    c.id === activeId ? "bg-aurora-50 text-aurora-700" : "hover:bg-paper-2"
                  }`}
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-aurora-100 text-xs font-semibold text-aurora-700">
                    {initials(peerName)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{peerName}</span>
                    <span className="block truncate text-xs text-ink-3">{c.last_text || "…"}</span>
                  </span>
                </button>
              </li>
            );
          })}
          {conversations.length === 0 && (
            <p className="px-2 py-4 text-sm text-ink-3">
              Переписки появляются автоматически, как только вас зачислят на курс.
            </p>
          )}
        </ul>
      </aside>

      <section className="flex flex-1 flex-col">
        {active ? (
          <>
            <header className="border-b border-line px-6 py-4">
              <p className="font-semibold">{peerId ? peerNames[peerId] ?? "…" : ""}</p>
            </header>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              <ul className="space-y-3">
                {messages.map((m) => {
                  const mine = m.sender_id === user?.id;
                  return (
                    <li key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[70%] rounded-2xl px-4 py-2.5 text-sm ${
                          mine ? "bg-aurora-600 text-white" : "bg-paper-2"
                        }`}
                      >
                        {m.attachment_url ? (
                          <a
                            href={m.attachment_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`underline ${mine ? "text-white" : "text-aurora-700"}`}
                          >
                            📎 {m.attachment_name || "Файл"}
                          </a>
                        ) : (
                          m.text
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
              <div ref={bottomRef} />
            </div>
            <div className="flex items-center gap-2 border-t border-line px-6 py-4">
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && void sendFile(e.target.files[0])}
              />
              <button
                className="btn btn-ghost !px-3 !py-2.5"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                title="Прикрепить файл"
              >
                📎
              </button>
              <input
                className="field flex-1"
                placeholder="Сообщение…"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void send()}
              />
              <button className="btn btn-primary !px-5" onClick={() => void send()}>
                Отправить
              </button>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-ink-3">
            Выберите переписку слева
          </div>
        )}
      </section>
    </div>
  );
}
