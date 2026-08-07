"""Realtime pub/sub for chat WebSockets."""

from __future__ import annotations

from edubridge_shared.realtime import RealtimeBus

from .core.config import get_settings

_settings = get_settings()
bus = RealtimeBus(_settings.realtime_redis_url)


def conversation_channel(conversation_id: str) -> str:
    return f"chat:{conversation_id}"
