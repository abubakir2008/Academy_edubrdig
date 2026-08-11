"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AsideList, AuthShell } from "@/components/auth-shell";
import { useAuth } from "@/lib/auth";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") ?? "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      router.push(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось войти");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="С возвращением"
      subtitle="Войдите, чтобы продолжить переписку с преподавателем и пользоваться AI-помощником."
      aside={
        <AsideList
          title="Ваш прогресс не теряется"
          items={[
            "Переписка с преподавателем всегда под рукой.",
            "AI-помощник помнит историю ваших запросов.",
            "Уведомления приходят сразу в кабинет.",
          ]}
        />
      }
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            className="field"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="password">
            Пароль
          </label>
          <input
            id="password"
            type="password"
            className="field"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && (
          <p className="rounded-xl bg-coral-100 px-4 py-3 text-sm text-coral-500">{error}</p>
        )}

        <button type="submit" className="btn btn-primary w-full" disabled={busy}>
          {busy ? "Входим…" : "Войти"}
        </button>
      </form>
    </AuthShell>
  );
}
