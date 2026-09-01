"""Push delivery via Expo's push API — mirrors email.py's fire-and-forget
shape (never raises; a bad/expired token just means one fewer notification,
not a broken request for the caller)."""

from __future__ import annotations

import logging

import httpx

from .core.config import get_settings

_settings = get_settings()
log = logging.getLogger(_settings.service_name)

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
# Expo caps a single push request at 100 messages.
_BATCH_SIZE = 100


async def send_push(tokens: list[str], title: str, body: str | None) -> None:
    if not _settings.push_enabled or not tokens:
        return
    messages = [{"to": token, "title": title, "body": body} for token in tokens]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for i in range(0, len(messages), _BATCH_SIZE):
                await client.post(_EXPO_PUSH_URL, json=messages[i : i + _BATCH_SIZE])
    except Exception as exc:  # never let a push failure break the caller
        log.warning("Push send failed for %d token(s): %s", len(tokens), exc)
