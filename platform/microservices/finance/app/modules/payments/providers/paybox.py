"""Paybox / FreedomPay adapter (Kyrgyzstan-friendly PSP).

Implements Paybox's documented signature scheme:
    pg_sig = md5( "<script_name>;<;-joined sorted pg_* values>;<secret_key>" )

⚠️ Before going live, confirm the exact endpoint, parameter names and the
signature field ordering against the Paybox/FreedomPay merchant docs you obtain
(they occasionally differ per merchant/region). Everything else in the payment
flow is provider-agnostic, so only this file changes.

Activate by setting in .env:
    PAYMENT_PROVIDER=paybox
    PAYBOX_MERCHANT_ID=...
    PAYBOX_SECRET_KEY=...
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET

import httpx

from .base import PaymentInit, PaymentProvider, WebhookResult

INIT_URL = "https://api.paybox.money/init_payment.php"
INIT_SCRIPT = "init_payment.php"


def _sign(script_name: str, params: dict[str, str], secret: str) -> str:
    ordered = [params[k] for k in sorted(params)]
    raw = ";".join([script_name, *ordered, secret])
    return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324 - required by Paybox


class PayboxProvider(PaymentProvider):
    name = "paybox"

    def __init__(self, merchant_id: str, secret_key: str) -> None:
        self._merchant = merchant_id
        self._secret = secret_key

    async def create(self, *, amount_cents, currency, order_id, description, return_url) -> PaymentInit:
        params = {
            "pg_merchant_id": self._merchant,
            "pg_order_id": order_id,
            "pg_amount": f"{amount_cents / 100:.2f}",
            "pg_currency": currency,
            "pg_description": description[:255] or "Lesson payment",
            "pg_result_url": return_url,       # server-to-server callback
            "pg_success_url": return_url,
            "pg_salt": order_id[:16],
        }
        params["pg_sig"] = _sign(INIT_SCRIPT, params, self._secret)

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(INIT_URL, data=params)
        root = ET.fromstring(resp.text)
        status = (root.findtext("pg_status") or "").strip()
        if status != "ok":
            msg = root.findtext("pg_error_description") or "Paybox init failed"
            raise RuntimeError(f"Paybox: {msg}")
        return PaymentInit(
            provider_ref=(root.findtext("pg_payment_id") or order_id).strip(),
            payment_url=(root.findtext("pg_redirect_url") or "").strip() or None,
            settled=False,
        )

    def parse_webhook(self, params: dict) -> WebhookResult:
        received = str(params.get("pg_sig", ""))
        to_sign = {k: str(v) for k, v in params.items() if k != "pg_sig"}
        expected = _sign("result", to_sign, self._secret)
        if received != expected:
            raise ValueError("Invalid Paybox signature")
        return WebhookResult(
            order_id=str(params.get("pg_order_id", "")),
            provider_ref=str(params.get("pg_payment_id", "")),
            succeeded=str(params.get("pg_result", "")) == "1",
        )
