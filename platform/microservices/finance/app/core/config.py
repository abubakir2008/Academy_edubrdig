"""Finance department configuration (payments + wallet)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field

from edubridge_shared.config import DepartmentSettings


class Settings(DepartmentSettings):
    service_name: str = "finance"
    db_schema: str = "finance"

    # Platform commission fraction withheld from each payment (0.0 - 1.0).
    commission_rate: float = Field(default=0.20, alias="PLATFORM_COMMISSION_RATE")

    # Payment gateway selection + credentials.
    payment_provider: str = Field(default="mock", alias="PAYMENT_PROVIDER")
    paybox_merchant_id: str = Field(default="", alias="PAYBOX_MERCHANT_ID")
    paybox_secret_key: str = Field(default="", alias="PAYBOX_SECRET_KEY")
    payment_return_url: str = Field(
        default="http://localhost/api/payments/webhook/paybox", alias="PAYMENT_RETURN_URL"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
