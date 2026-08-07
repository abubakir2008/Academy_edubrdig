"""Redis pub/sub helper for WebSocket fan-out.

Lets multiple service instances push realtime messages to connected clients:
one instance publishes to a channel, whichever instance holds the client's
WebSocket is subscribed and forwards it.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as aioredis


class RealtimeBus:
    def __init__(self, redis_url: str) -> None:
        self._redis = aioredis.from_url(redis_url, decode_responses=True)

    async def publish(self, channel: str, data: dict[str, Any]) -> None:
        await self._redis.publish(channel, json.dumps(data, default=str))

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    try:
                        yield json.loads(message["data"])
                    except (ValueError, TypeError):
                        continue
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
