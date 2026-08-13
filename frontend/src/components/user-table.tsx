"use client";

import { useMemo, useState } from "react";
import { Download, KeyRound, Pencil, Search, Trash2, X, Check } from "lucide-react";

import type { AdminUser, Role } from "@/lib/types";

const PAGE_SIZE = 10;

type Tab = "all" | "active" | "archived";
const TABS: { value: Tab; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "active", label: "Активные" },
  { value: "archived", label: "Архив" },
];

/** Accounts created for the phone-based bulk imports use `<phone>@...` as
 * their login — there's no dedicated phone field on the platform, so this
 * is the only place a phone number is recoverable from. Anything else
 * (a normal email) just shows no phone. */
function phoneFromEmail(email: string): string | null {
  const local = email.split("@")[0];
  return /^\d{6,}$/.test(local) ? local : null;
}

export type EditForm = { full_name: string; role: Role; is_active: boolean; is_verified: boolean };

/**
 * Students/tutors as a searchable, filterable, paginated table — the same
 * shape as any admin roster (Excel-style: name, login, phone, status, date,
 * row actions), replacing the card grid for these two roles specifically.
 * Staff ("Остальные роли") intentionally keeps the old card layout — it's a
 * short, rarely-changing list where a table adds nothing.
 */
export function UserTable({
  title,
  users,
  createLabel,
  onCreateClick,
  editingId,
  editForm,
  setEditForm,
  onEdit,
  onSave,
  onCancel,
  onDelete,
  onResetPassword,
}: {
  title: string;
  users: AdminUser[];
  createLabel: string;
  onCreateClick: () => void;
  editingId: string | null;
  editForm: EditForm | null;
  setEditForm: (f: EditForm | null) => void;
  onEdit: (u: AdminUser) => void;
  onSave: (id: string) => void;
  onCancel: () => void;
  onDelete: (u: AdminUser) => void;
  onResetPassword: (u: AdminUser) => void;
}) {
  const [tab, setTab] = useState<Tab>("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    let list = users;
    if (tab === "active") list = list.filter((u) => u.is_active);
    if (tab === "archived") list = list.filter((u) => !u.is_active);
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (u) => (u.full_name ?? "").toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
      );
    }
    return list;
  }, [users, tab, query]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, totalPages - 1);
  const pageItems = filtered.slice(current * PAGE_SIZE, current * PAGE_SIZE + PAGE_SIZE);

  function exportCsv() {
    const header = ["ФИО", "Логин", "Телефон", "Статус", "Дата регистрации"];
    const rows = filtered.map((u) => [
      u.full_name || "",
      u.email,
      phoneFromEmail(u.email) || "",
      u.is_active ? "Активен" : "Архив",
      new Date(u.created_at).toLocaleDateString("ru-RU"),
    ]);
    const csv = [header, ...rows].map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="mt-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="display text-lg">
          {title} <span className="text-sm font-normal text-ink-3">· {users.length}</span>
        </h2>
        <div className="flex gap-2">
          <button className="btn btn-ghost !py-2 text-sm" onClick={exportCsv}>
            <Download className="h-4 w-4" aria-hidden /> Экспорт
          </button>
          <button className="btn btn-primary !py-2 text-sm" onClick={onCreateClick}>
            + {createLabel}
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => {
                setTab(t.value);
                setPage(0);
              }}
              className={`chip ${tab === t.value ? "!border-aurora-600 !bg-aurora-600 !text-white" : ""}`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" aria-hidden />
          <input
            className="field !pl-9 text-sm"
            placeholder="Поиск по имени, email…"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
          />
        </div>
      </div>

      <div className="mt-4 overflow-x-auto rounded-2xl border border-line">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line bg-paper-2 text-left text-xs text-ink-3">
              <th className="px-4 py-3 font-medium">ФИО</th>
              <th className="px-4 py-3 font-medium">Логин</th>
              <th className="px-4 py-3 font-medium">Телефон</th>
              <th className="px-4 py-3 font-medium">Статус</th>
              <th className="px-4 py-3 font-medium">Дата</th>
              <th className="px-4 py-3 font-medium">Действия</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((u) => {
              const isEditing = editingId === u.id && editForm;
              return (
                <tr key={u.id} className="border-b border-line/60 last:border-0">
                  <td className="px-4 py-3 font-semibold">
                    {isEditing ? (
                      <input
                        className="field !py-1.5 text-sm"
                        value={editForm.full_name}
                        onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                      />
                    ) : (
                      u.full_name || "Без имени"
                    )}
                  </td>
                  <td className="px-4 py-3 text-ink-2">{u.email}</td>
                  <td className="px-4 py-3 text-ink-2">{phoneFromEmail(u.email) || "—"}</td>
                  <td className="px-4 py-3">
                    {isEditing ? (
                      <label className="flex items-center gap-1.5 text-xs">
                        <input
                          type="checkbox"
                          checked={editForm.is_active}
                          onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                        />
                        Активен
                      </label>
                    ) : (
                      <span
                        className={`chip ${
                          u.is_active ? "!border-jade-100 !bg-jade-100 !text-jade-700" : "!border-coral-100 !bg-coral-100 !text-coral-500"
                        }`}
                      >
                        {u.is_active ? "Активный" : "Архив"}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-ink-2">
                    {new Date(u.created_at).toLocaleDateString("ru-RU")}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {isEditing ? (
                        <>
                          <button
                            className="rounded-lg p-1.5 text-jade-700 hover:bg-jade-100"
                            title="Сохранить"
                            onClick={() => onSave(u.id)}
                          >
                            <Check className="h-4 w-4" aria-hidden />
                          </button>
                          <button
                            className="rounded-lg p-1.5 text-ink-3 hover:bg-paper-2"
                            title="Отмена"
                            onClick={onCancel}
                          >
                            <X className="h-4 w-4" aria-hidden />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className="rounded-lg p-1.5 text-ink-2 hover:bg-paper-2"
                            title="Изменить"
                            onClick={() => onEdit(u)}
                          >
                            <Pencil className="h-4 w-4" aria-hidden />
                          </button>
                          <button
                            className="flex items-center gap-1 rounded-full bg-citrus-100 px-2.5 py-1 text-xs font-semibold text-citrus-700 hover:bg-citrus-100/70"
                            title="Сбросить пароль"
                            onClick={() => onResetPassword(u)}
                          >
                            <KeyRound className="h-3.5 w-3.5" aria-hidden /> Пароль
                          </button>
                          <button
                            className="rounded-lg p-1.5 text-coral-500 hover:bg-coral-100"
                            title="Удалить"
                            onClick={() => onDelete(u)}
                          >
                            <Trash2 className="h-4 w-4" aria-hidden />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {pageItems.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-ink-3">
                  Никого не нашлось.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-4">
          <button className="btn btn-ghost !py-1.5 text-xs" disabled={current === 0} onClick={() => setPage(current - 1)}>
            ← Назад
          </button>
          <span className="text-xs text-ink-3">
            Стр. {current + 1} из {totalPages} · {filtered.length} всего
          </span>
          <button
            className="btn btn-ghost !py-1.5 text-xs"
            disabled={current === totalPages - 1}
            onClick={() => setPage(current + 1)}
          >
            Дальше →
          </button>
        </div>
      )}
    </section>
  );
}
