"""Payment provider selection."""

from __future__ import annotations

from functools import lru_cache

from ..core.config import get_settings
from .base import PaymentProvider
from .mock import MockProvider
from .paybox import PayboxProvider


@lru_cache
def get_provider() -> PaymentProvider:
    s = get_settings()
    if s.payment_provider == "mock":
        return MockProvider()
    if s.payment_provider == "paybox":
        if not (s.paybox_merchant_id and s.paybox_secret_key):
            # A deployment that asked for "paybox" but forgot the credentials
            # used to fall through to MockProvider — real money would look
            # like it was collected while nothing was ever charged. Fail the
            # first payment attempt loudly instead of degrading silently.
            raise RuntimeError(
                "PAYMENT_PROVIDER=paybox but PAYBOX_MERCHANT_ID/PAYBOX_SECRET_KEY "
                "are not set — refusing to silently fall back to the mock provider"
            )
        return PayboxProvider(s.paybox_merchant_id, s.paybox_secret_key)
    raise RuntimeError(f"Unknown PAYMENT_PROVIDER={s.payment_provider!r}")
