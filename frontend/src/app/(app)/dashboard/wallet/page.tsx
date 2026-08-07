"use client";

import { useCallback, useEffect, useState } from "react";

import { get, post } from "@/lib/api";
import { money } from "@/lib/format";
import type { PayoutMethod, Wallet, WalletTransaction, Withdrawal } from "@/lib/types";

const METHODS: { id: PayoutMethod; label: string; placeholder: string }[] = [
  { id: "bank_card", label: "Банковская карта", placeholder: "0000 0000 0000 0000" },
  { id: "mobile_wallet", label: "Мобильный кошелёк", placeholder: "+996 700 000 000" },
  { id: "crypto", label: "Криптокошелёк (USDT)", placeholder: "TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
  { id: "paypal", label: "PayPal", placeholder: "you@example.com" },
];

export default function WalletPage() {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [txs, setTxs] = useState<WalletTransaction[]>([]);
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
  const [busy, setBusy] = useState(true);

  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PayoutMethod>("bank_card");
  const [destination, setDestination] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    const [w, t, wd] = await Promise.all([
      get<Wallet>("/wallet/me", true).catch(() => null),
      get<WalletTransaction[]>("/wallet/me/transactions", true).catch(() => [] as WalletTransaction[]),
      get<Withdrawal[]>("/wallet/me/withdrawals", true).catch(() => [] as Withdrawal[]),
    ]);
    setWallet(w);
    setTxs(t);
    setWithdrawals(wd);
    setBusy(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function requestWithdrawal() {
    setError(null);
    const cents = Math.round(Number(amount) * 100);
    if (!cents || cents <= 0) {
      setError("Укажите сумму");
      return;
    }
    if (!destination.trim()) {
      setError("Укажите реквизиты для выплаты");
      return;
    }
    setRequesting(true);
    try {
      await post("/wallet/me/withdrawals", { amount_cents: cents, method, destination }, true);
      setAmount("");
      setDestination("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать заявку");
    } finally {
      setRequesting(false);
    }
  }

  const activeMethod = METHODS.find((m) => m.id === method)!;

  return (
    <div className="mx-auto max-w-4xl px-5 py-8 lg:py-12">
      <header>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-aurora-600">Кошелёк</p>
        <h1 className="display mt-2 text-[clamp(1.75rem,3.5vw,2.75rem)]">Баланс и выплаты</h1>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-8">
          <section>
            <h2 className="display text-lg">История операций</h2>
            {busy ? (
              <div className="card mt-4 h-24 animate-pulse bg-line/40" />
            ) : txs.length ? (
              <ul className="mt-4 space-y-2">
                {txs.map((t) => (
                  <li key={t.id} className="card flex items-center justify-between gap-4 p-4">
                    <div>
                      <p className="text-sm font-medium">{t.description || t.type}</p>
                      <p className="text-xs text-ink-3">{new Date(t.created_at).toLocaleString("ru-RU")}</p>
                    </div>
                    <span className={`font-semibold ${t.amount_cents >= 0 ? "text-jade-700" : "text-coral-500"}`}>
                      {t.amount_cents >= 0 ? "+" : ""}
                      {money(t.amount_cents, wallet?.currency)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="card mt-4 p-6 text-sm text-ink-3">Операций пока нет.</p>
            )}
          </section>

          <section>
            <h2 className="display text-lg">Заявки на выплату</h2>
            {withdrawals.length ? (
              <ul className="mt-4 space-y-2">
                {withdrawals.map((w) => (
                  <li key={w.id} className="card flex items-center justify-between gap-4 p-4">
                    <div>
                      <p className="text-sm font-medium">
                        {METHODS.find((m) => m.id === w.method)?.label ?? w.method}
                      </p>
                      <p className="text-xs text-ink-3">{new Date(w.created_at).toLocaleDateString("ru-RU")}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">{money(w.amount_cents, w.currency)}</p>
                      <span className="chip text-xs">{w.status}</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="card mt-4 p-6 text-sm text-ink-3">Заявок ещё не было.</p>
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <div className="card p-6">
            <p className="text-sm text-ink-3">Доступно к выводу</p>
            <p className="display mt-1 text-3xl">
              {wallet ? money(wallet.balance_cents, wallet.currency) : "—"}
            </p>
          </div>

          <div className="card p-6">
            <h2 className="display text-lg">Вывести средства</h2>
            <div className="mt-4 space-y-3">
              <div>
                <label className="label">Сумма</label>
                <input
                  className="field"
                  inputMode="decimal"
                  placeholder="0.00"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
              <div>
                <label className="label">Способ выплаты</label>
                <select
                  className="field"
                  value={method}
                  onChange={(e) => setMethod(e.target.value as PayoutMethod)}
                >
                  {METHODS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Реквизиты</label>
                <input
                  className="field"
                  placeholder={activeMethod.placeholder}
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                />
              </div>
              {error && <p className="text-sm text-coral-500">{error}</p>}
              <button
                className="btn btn-primary w-full !py-2.5 text-sm"
                disabled={requesting}
                onClick={() => void requestWithdrawal()}
              >
                {requesting ? "Отправляем…" : "Запросить выплату"}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
