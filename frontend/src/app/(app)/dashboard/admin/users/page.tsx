"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ApiError, del, get, post, put } from "@/lib/api";
import { Paginated } from "@/components/paginated";
import type { AdminUser, AdminUserCreated, PasswordIssued, Role } from "@/lib/types";

const ROLE_LABELS: Record<Role, string> = {
  student: "Ученик",
  tutor: "Репетитор",
  admin: "Админ",
  super_admin: "Супер-админ",
  moderator: "Модератор",
};

const STAFF_ROLES: Role[] = ["admin", "super_admin", "moderator"];

const EMPTY_CREATE = { email: "", full_name: "", role: "student" as Role };
type EditForm = { full_name: string; role: Role; is_active: boolean; is_verified: boolean };

/** Issued once, right after creation or a password reset — there is no other
 * way to retrieve a password afterwards (only the bcrypt hash is stored). */
type Credentials = { email: string; password: string };

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [credentials, setCredentials] = useState<Credentials | null>(null);

  const [createForm, setCreateForm] = useState(EMPTY_CREATE);
  const [creating, setCreating] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const list = await get<AdminUser[]>("/auth/admin/users", true).catch(() => [] as AdminUser[]);
    setUsers(list);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function createUser() {
    if (!createForm.email) return;
    setCreating(true);
    setError(null);
    try {
      const result = await post<AdminUserCreated>(
        "/auth/admin/users",
        { email: createForm.email, full_name: createForm.full_name || null, role: createForm.role },
        true,
      );
      setCredentials({ email: result.user.email, password: result.password });
      setCreateForm(EMPTY_CREATE);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось создать пользователя");
    } finally {
      setCreating(false);
    }
  }

  function startEdit(u: AdminUser) {
    setEditingId(u.id);
    setEditForm({ full_name: u.full_name ?? "", role: u.role, is_active: u.is_active, is_verified: u.is_verified });
  }

  async function saveEdit(id: string) {
    if (!editForm) return;
    await put(`/auth/admin/users/${id}`, editForm, true).catch(() => undefined);
    setEditingId(null);
    setEditForm(null);
    await load();
  }

  async function removeUser(u: AdminUser) {
    if (!window.confirm(`Удалить пользователя ${u.email}? Это необратимо.`)) return;
    await del(`/auth/admin/users/${u.id}`).catch(() => undefined);
    await load();
  }

  async function resetPassword(u: AdminUser) {
    if (!window.confirm(`Сгенерировать новый пароль для ${u.email}? Старый перестанет работать.`)) return;
    const result = await post<PasswordIssued>(`/auth/admin/users/${u.id}/reset-password`, undefined, true).catch(
      () => null,
    );
    if (result) setCredentials({ email: u.email, password: result.password });
  }

  const tutors = users.filter((u) => u.role === "tutor");
  const students = users.filter((u) => u.role === "student");
  const staff = users.filter((u) => STAFF_ROLES.includes(u.role));

  return (
    <div className="mx-auto max-w-6xl px-5 py-8 lg:py-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Админ</p>
          <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Пользователи</h1>
        </div>
        <Link href="/dashboard/admin" className="btn btn-ghost">
          ← Панель управления
        </Link>
      </header>

      {credentials && (
        <div className="card mt-6 flex flex-wrap items-center justify-between gap-4 border-aurora-300 bg-aurora-50 p-5">
          <div className="text-sm">
            <p className="font-semibold text-aurora-700">Логин и пароль — сохраните сейчас, второй раз не покажем</p>
            <p className="mt-1">
              Логин: <b className="font-semibold">{credentials.email}</b> · Пароль:{" "}
              <b className="font-mono font-semibold">{credentials.password}</b>
            </p>
          </div>
          <div className="flex gap-2">
            <button
              className="btn btn-ghost !py-1.5 text-xs"
              onClick={() => void navigator.clipboard.writeText(`${credentials.email} / ${credentials.password}`)}
            >
              Скопировать
            </button>
            <button className="btn btn-ghost !py-1.5 text-xs" onClick={() => setCredentials(null)}>
              Закрыть
            </button>
          </div>
        </div>
      )}

      <section className="mt-8">
        <h2 className="display text-lg">Создать пользователя</h2>
        <div className="card mt-4 p-6">
          <div className="grid gap-3 sm:grid-cols-3">
            <input
              className="field"
              type="email"
              placeholder="email"
              value={createForm.email}
              onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
            />
            <input
              className="field"
              placeholder="Имя (необязательно)"
              value={createForm.full_name}
              onChange={(e) => setCreateForm((f) => ({ ...f, full_name: e.target.value }))}
            />
            <select
              className="field"
              value={createForm.role}
              onChange={(e) => setCreateForm((f) => ({ ...f, role: e.target.value as Role }))}
            >
              {Object.entries(ROLE_LABELS).map(([role, label]) => (
                <option key={role} value={role}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <p className="mt-2 text-xs text-ink-3">
            Пароль сгенерируется автоматически и покажется один раз сразу после создания.
          </p>
          {error && <p className="mt-2 text-xs text-coral-500">{error}</p>}
          <button className="btn btn-primary mt-3 !py-2 text-sm" onClick={() => void createUser()} disabled={creating}>
            {creating ? "Создаём…" : "Создать"}
          </button>
        </div>
      </section>

      {loading ? (
        <p className="mt-8 text-sm text-ink-3">Загрузка…</p>
      ) : (
        <>
          <UserGroup
            title="Репетиторы"
            users={tutors}
            editingId={editingId}
            editForm={editForm}
            setEditForm={setEditForm}
            onEdit={startEdit}
            onSave={saveEdit}
            onCancel={() => setEditingId(null)}
            onDelete={removeUser}
            onResetPassword={resetPassword}
          />
          <UserGroup
            title="Ученики"
            users={students}
            editingId={editingId}
            editForm={editForm}
            setEditForm={setEditForm}
            onEdit={startEdit}
            onSave={saveEdit}
            onCancel={() => setEditingId(null)}
            onDelete={removeUser}
            onResetPassword={resetPassword}
          />
          <UserGroup
            title="Остальные роли (персонал)"
            users={staff}
            editingId={editingId}
            editForm={editForm}
            setEditForm={setEditForm}
            onEdit={startEdit}
            onSave={saveEdit}
            onCancel={() => setEditingId(null)}
            onDelete={removeUser}
            onResetPassword={resetPassword}
          />
        </>
      )}
    </div>
  );
}

/* ------------------------------ Pieces --------------------------------- */

function UserGroup({
  title,
  users,
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
  editingId: string | null;
  editForm: EditForm | null;
  setEditForm: (f: EditForm | null) => void;
  onEdit: (u: AdminUser) => void;
  onSave: (id: string) => void;
  onCancel: () => void;
  onDelete: (u: AdminUser) => void;
  onResetPassword: (u: AdminUser) => void;
}) {
  return (
    <section className="mt-10">
      <h2 className="display text-lg">
        {title} <span className="text-sm font-normal text-ink-3">· {users.length}</span>
      </h2>
      <Paginated
        items={users}
        empty="Пока никого нет."
        renderItem={(u) => (
          <li key={u.id} className="card h-full p-4 text-sm">
            {editingId === u.id && editForm ? (
              <div className="space-y-2">
                <input
                  className="field text-sm"
                  placeholder="Имя"
                  value={editForm.full_name}
                  onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                />
                <select
                  className="field text-sm"
                  value={editForm.role}
                  onChange={(e) => setEditForm({ ...editForm, role: e.target.value as Role })}
                >
                  {Object.entries(ROLE_LABELS).map(([role, label]) => (
                    <option key={role} value={role}>
                      {label}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-2 text-xs text-ink-2">
                  <input
                    type="checkbox"
                    checked={editForm.is_active}
                    onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                  />
                  Активен
                </label>
                <label className="flex items-center gap-2 text-xs text-ink-2">
                  <input
                    type="checkbox"
                    checked={editForm.is_verified}
                    onChange={(e) => setEditForm({ ...editForm, is_verified: e.target.checked })}
                  />
                  Подтверждён
                </label>
                <div className="flex gap-2 pt-1">
                  <button className="btn btn-primary !py-1.5 text-xs" onClick={() => onSave(u.id)}>
                    Сохранить
                  </button>
                  <button className="btn btn-ghost !py-1.5 text-xs" onClick={onCancel}>
                    Отмена
                  </button>
                </div>
              </div>
            ) : (
              <>
                <b className="block truncate font-semibold" title={u.email}>
                  {u.email}
                </b>
                <p className="mt-0.5 text-ink-3">{u.full_name || "Без имени"}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <span className="chip">{ROLE_LABELS[u.role]}</span>
                  <span className={`chip ${u.is_active ? "text-jade-700" : "text-coral-500"}`}>
                    {u.is_active ? "Активен" : "Отключён"}
                  </span>
                  {!u.is_verified && <span className="chip text-citrus-700">Не подтверждён</span>}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button className="btn btn-ghost !py-1.5 text-xs" onClick={() => onEdit(u)}>
                    Изменить
                  </button>
                  <button className="btn btn-ghost !py-1.5 text-xs" onClick={() => onResetPassword(u)}>
                    Сбросить пароль
                  </button>
                  <button className="btn btn-ghost !py-1.5 text-xs text-coral-500" onClick={() => onDelete(u)}>
                    Удалить
                  </button>
                </div>
              </>
            )}
          </li>
        )}
      />
    </section>
  );
}
