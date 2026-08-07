"use client";

import { useCallback, useEffect, useState } from "react";

import { get, post } from "@/lib/api";
import { money } from "@/lib/format";
import type { Withdrawal } from "@/lib/types";

export default function PayoutsPage() {
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const [tutorId, setTutorId] = useState("");
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [creditError, setCreditError] = useState<string | null>(null);
  const [creditOk, setCreditOk] = useState(false);

  const load = useCallback(async () => {
    const items = await get<Withdrawal[]>("/wallet/withdrawals?status=requested", true).catch(
      () => [] as Withdrawal[],
    );
    setWithdrawals(items);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(id: string, action: "approve" | "reject") {
    setBusy(id);
    await post(`/wallet/withdrawals/${id}/${action}`, undefined, true).catch(() => undefined);
    await load();
    setBusy(null);
  }

  async function creditWallet() {
    setCreditError(null);
    setCreditOk(false);
    const cents = Math.round(Number(amount) * 100);
    if (!tutorId || !cents) {
      setCreditError("Укажите ID репетитора и сумму");
      return;
    }
    try {
      await post(
        "/wallet/credit",
        { tutor_id: tutorId, amount_cents: cents, reference: reference || undefined },
        true,
      );
      setCreditOk(true);
      setTutorId("");
      setAmount("");
      setReference("");
    } catch (e) {
      setCreditError(e instanceof Error ? e.message : "Не удалось начислить");
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Выплаты</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Заявки на вывод</h1>
      </header>

      <section className="mt-8">
        {withdrawals.length ? (
          <ul className="space-y-3">
            {withdrawals.map((w) => (
              <li key={w.id} className="card flex flex-wrap items-center justify-between gap-3 p-5">
                <div>
                  <p className="font-semibold">{money(w.amount_cents, w.currency)}</p>
                  <p className="mt-1 text-sm text-ink-3">
                    {w.method} · {w.destination} · репетитор {w.tutor_id.slice(0, 8)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    className="btn btn-primary !py-2 text-sm"
                    disabled={busy === w.id}
                    onClick={() => void act(w.id, "approve")}
                  >
                    Одобрить
                  </button>
                  <button
                    className="btn btn-ghost !py-2 text-sm"
                    disabled={busy === w.id}
                    onClick={() => void act(w.id, "reject")}
                  >
                    Отклонить
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="card p-6 text-sm text-ink-3">Заявок на рассмотрении нет.</p>
        )}
      </section>

      <section className="card mt-8 p-6">
        <h2 className="display text-lg">Ручное начисление</h2>
        <p className="mt-1 text-sm text-ink-3">Кредит кошельку репетитора (корректировки, бонусы).</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <input className="field" placeholder="ID репетитора" value={tutorId} onChange={(e) => setTutorId(e.target.value)} />
          <input className="field" placeholder="Сумма" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
          <input className="field" placeholder="Референс (необязательно)" value={reference} onChange={(e) => setReference(e.target.value)} />
        </div>
        {creditError && <p className="mt-2 text-sm text-coral-500">{creditError}</p>}
        {creditOk && <p className="mt-2 text-sm text-jade-700">✓ Начислено</p>}
        <button className="btn btn-primary mt-3 !py-2 text-sm" onClick={() => void creditWallet()}>
          Начислить
        </button>
      </section>
    </div>
  );
}
