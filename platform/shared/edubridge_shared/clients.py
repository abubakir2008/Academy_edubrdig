"""Service-to-service HTTP: a typed client and the guard for the other side.

Used sparingly for synchronous lookups that must be authoritative *now*.
Anything that can be eventual stays on the event bus instead.

Internal calls carry a shared secret in ``X-Internal-Secret``. Endpoints that
only another department should reach depend on :func:`require_internal`, so
network isolation is no longer the only thing standing between the public
internet and internal routes.
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Any

import httpx
from fastapi import Header, HTTPException, status

log = logging.getLogger("clients")

INTERNAL_HEADER = "X-Internal-Secret"

#: Which department serves which legacy route prefix. Route prefixes are part of
#: the public API and never change; only their home moves.
SERVICE_DEPARTMENT: dict[str, str] = {
    "auth": "identity",
    "users": "identity",
    "chat": "engagement",
    "notifications": "engagement",
    "support": "engagement",
    "cms": "content",
    "localization": "content",
    "ai": "content",
    "storage": "content",
    "admin": "backoffice",
    "analytics": "backoffice",
    "courses": "academics",
    "calendar": "calendar",
}


class ServiceError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(f"{status}: {detail}")


def internal_secret() -> str:
    return os.getenv("INTERNAL_SECRET", "")


def service_url(name: str, default_host: str | None = None) -> str:
    """Resolve a base URL for a route prefix, e.g. ``chat`` -> engagement.

    An explicit ``<NAME>_URL`` env var always wins, which is what the test suite
    and any split-out deployment use.
    """
    explicit = os.getenv(f"{name.upper()}_URL")
    if explicit:
        return explicit
    host = default_host or SERVICE_DEPARTMENT.get(name, name)
    return f"http://{host}:8000"


class ServiceClient:
    """Small async client wrapping one downstream base URL.

    Holds a single ``AsyncClient`` so connections are pooled and reused rather
    than a fresh TCP + handshake per call — noticeable on a small host.
    """

    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    def _headers(self, token: str | None) -> dict[str, str]:
        headers: dict[str, str] = {}
        secret = internal_secret()
        if secret:
            headers[INTERNAL_HEADER] = secret
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _request(
        self, method: str, path: str, *, token: str | None, json: Any | None = None
    ) -> Any:
        try:
            resp = await self._http().request(
                method, f"{self._base}{path}", headers=self._headers(token), json=json
            )
        except httpx.HTTPError as exc:
            raise ServiceError(503, f"upstream unreachable: {exc}") from exc
        if resp.status_code >= 400:
            raise ServiceError(resp.status_code, resp.text)
        return resp.json()

    async def get(self, path: str, *, token: str | None = None) -> Any:
        return await self._request("GET", path, token=token)

    async def post(self, path: str, json: Any | None = None, *, token: str | None = None) -> Any:
        return await self._request("POST", path, token=token, json=json)

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


async def require_internal(
    x_internal_secret: str | None = Header(default=None, alias=INTERNAL_HEADER),
) -> None:
    """FastAPI dependency: reject anything that isn't a trusted internal caller.

    With no secret configured the guard is a no-op so local development works
    out of the box; production sets ``INTERNAL_SECRET`` and the compose file
    passes it to every department.
    """
    expected = internal_secret()
    if not expected:
        log.warning("INTERNAL_SECRET is unset — internal endpoints are unguarded")
        return
    if not x_internal_secret or not hmac.compare_digest(x_internal_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Internal endpoint"
        )
