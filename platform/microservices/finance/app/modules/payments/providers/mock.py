"""Mock provider — settles instantly. Default for local dev and E2E tests."""

from __future__ import annotations

from .base import PaymentInit, PaymentProvider, WebhookResult


class MockProvider(PaymentProvider):
    name = "mock"

    async def create(self, *, amount_cents, currency, order_id, description, return_url) -> PaymentInit:
        return PaymentInit(provider_ref=f"mock_{order_id}", payment_url=None, settled=True)

    def parse_webhook(self, params: dict) -> WebhookResult:
        return WebhookResult(
            order_id=str(params.get("order_id", "")),
            provider_ref=str(params.get("provider_ref", "")),
            succeeded=str(params.get("status", "success")) == "success",
        )
