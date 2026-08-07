"""Realtime pub/sub for notification WebSockets."""

from __future__ import annotations

from edubridge_shared.realtime import RealtimeBus

from .core.config import get_settings

_settings = get_settings()
bus = RealtimeBus(_settings.realtime_redis_url)


def user_channel(user_id: str) -> str:
    return f"notif:{user_id}"
