"""Payment provider abstraction.

Adding a new gateway (Paybox/FreedomPay, a bank acquirer, a wallet) means writing
one subclass — the checkout flow, commission split, wallet crediting and receipts
stay unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PaymentInit:
    provider_ref: str
    # Where to redirect the payer. None when the provider settles synchronously
    # (e.g. the mock provider used in tests/dev).
    payment_url: str | None
    settled: bool


@dataclass
class WebhookResult:
    order_id: str          # our payment id
    provider_ref: str
    succeeded: bool


class PaymentProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def create(
        self,
        *,
        amount_cents: int,
        currency: str,
        order_id: str,
        description: str,
        return_url: str,
    ) -> PaymentInit:
        ...

    @abstractmethod
    def parse_webhook(self, params: dict) -> WebhookResult:
        """Verify the callback signature and extract the outcome."""
        ...
