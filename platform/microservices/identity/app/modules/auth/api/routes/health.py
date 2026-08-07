"""Health / readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from edubridge_shared.schemas import HealthResponse

from ... import __version__
from ...core.config import get_settings
from ...services import token_store

router = APIRouter(tags=["health"])
_settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=_settings.service_name, version=__version__)


@router.get("/ready")
async def ready() -> dict[str, bool]:
    return {"redis": await token_store.ping()}
