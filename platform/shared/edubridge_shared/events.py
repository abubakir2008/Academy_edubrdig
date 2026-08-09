"""Event bus for choreography between departments, built on Redis Streams.

Why Redis Streams and not Kafka: this platform runs on a single small host.
Kafka's broker alone wants more memory than every application container
combined, and Streams give us the two properties we actually depend on —
durable, replayable log + per-consumer-group cursors — out of the Redis instance
we already run.

Delivery guarantees, and how they differ from the previous Kafka wiring:

- **Nothing is acknowledged until its handler returns.** ``XREADGROUP`` hands a
  message to exactly one consumer in the group and records it as *pending*;
  :meth:`_handle` only calls ``XACK`` after every handler for that topic
  succeeded. A crash mid-handler therefore leaves the message pending and it
  gets reclaimed, instead of being silently dropped by an auto-commit.
- **Stalled work is reclaimed.** ``XAUTOCLAIM`` picks up messages left pending
  by a dead consumer for longer than ``claim_idle_ms``.
- **Redelivery is suppressed.** Before dispatching, the consumer marks the
  event id in Redis (``SET NX``); an event already marked is acked and skipped.
  This closes the ordinary duplicate case. Handlers with side effects that
  aren't naturally idempotent must still guard themselves for the
  crash-after-handler-before-mark window.
- **Poison messages are quarantined.** After ``max_attempts`` failed deliveries
  the event is moved to ``<topic>:dead`` and acked, so one bad payload can never
  block the stream forever.

Publishing stays best-effort: a Redis hiccup must never fail the HTTP request
that triggered the event.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import socket
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

log = logging.getLogger("events")

Handler = Callable[[dict[str, Any], str], Awaitable[None]]

#: How long a processed-event marker is remembered (7 days).
DEDUPE_TTL_SECONDS = 7 * 24 * 3600


class Topics:
    """Canonical event topic names shared by producers and consumers."""

    USER_REGISTERED = "auth.user_registered"


def _envelope(topic: str, data: dict[str, Any], producer: str) -> dict[str, Any]:
    return {
        "event_type": topic,
        "producer": producer,
        "occurred_at": datetime.now(tz=timezone.utc).isoformat(),
        "data": data,
    }


class EventBus:
    """One instance per department. Publishes events and/or consumes them.

    Each department consumes under its own group name, so every subscriber
    receives its own copy of every event (fan-out), exactly as before.
    """

    def __init__(
        self,
        *,
        redis_url: str,
        service_name: str,
        maxlen: int = 10_000,
        block_ms: int = 5_000,
        claim_idle_ms: int = 60_000,
        max_attempts: int = 5,
    ) -> None:
        self._url = redis_url
        self._service = service_name
        self._maxlen = maxlen
        self._block_ms = block_ms
        self._claim_idle_ms = claim_idle_ms
        self._max_attempts = max_attempts
        self._consumer_name = f"{service_name}-{socket.gethostname()}-{uuid.uuid4().hex[:6]}"
        self._redis: aioredis.Redis | None = None
        self._handlers: dict[str, list[Handler]] = {}
        self._task: asyncio.Task | None = None
        self._stopping = False

    # ------------------------------ Connection ---------------------------

    async def _client(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._url, decode_responses=True)
        return self._redis

    # ------------------------------- Producer ----------------------------

    async def start_producer(self) -> None:
        """Pre-warm the Redis connection. Optional: publish() connects lazily too."""
        try:
            await self._client()
        except Exception as exc:  # Redis not ready yet — publish() will retry later
            log.warning("Event bus could not pre-connect: %s", exc)

    async def publish(self, topic: str, data: dict[str, Any], *, key: str | None = None) -> None:
        """Best-effort publish; never raises into the caller's request path.

        ``key`` is accepted for call-site compatibility with the previous Kafka
        bus. Streams have a single partition per topic, so ordering is already
        total and the key is recorded for traceability only.
        """
        payload = _envelope(topic, data, self._service)
        if key:
            payload["key"] = key
        try:
            redis = await self._client()
            await redis.xadd(
                topic,
                {"payload": json.dumps(payload, default=str)},
                maxlen=self._maxlen,
                approximate=True,
            )
        except Exception as exc:
            log.warning("Failed to publish %s: %s", topic, exc)

    # ------------------------------- Consumer ----------------------------

    def on(self, topic: str, handler: Handler) -> None:
        self._handlers.setdefault(topic, []).append(handler)

    async def start_consuming(self) -> None:
        if not self._handlers:
            return
        self._task = asyncio.create_task(self._consume_loop())

    async def _ensure_groups(self, redis: aioredis.Redis) -> None:
        for topic in self._handlers:
            with contextlib.suppress(aioredis.ResponseError):  # BUSYGROUP = already there
                await redis.xgroup_create(topic, self._service, id="0", mkstream=True)

    async def _consume_loop(self) -> None:
        while not self._stopping:
            try:
                redis = await self._client()
                await self._ensure_groups(redis)
                log.info(
                    "Event consumer %s listening on %s",
                    self._consumer_name,
                    list(self._handlers),
                )
                while not self._stopping:
                    await self._reclaim_stalled(redis)
                    batches = await redis.xreadgroup(
                        groupname=self._service,
                        consumername=self._consumer_name,
                        streams=dict.fromkeys(self._handlers, ">"),
                        count=32,
                        block=self._block_ms,
                    )
                    for topic, entries in batches or []:
                        for entry_id, fields in entries:
                            await self._handle(redis, topic, entry_id, fields)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not self._stopping:
                    log.warning("Event consumer error (%s); reconnecting in 5s", exc)
                    self._redis = None
                    await asyncio.sleep(5)

    async def _reclaim_stalled(self, redis: aioredis.Redis) -> None:
        """Take over messages a dead consumer left pending."""
        for topic in self._handlers:
            try:
                _, entries, _ = await redis.xautoclaim(
                    topic,
                    self._service,
                    self._consumer_name,
                    min_idle_time=self._claim_idle_ms,
                    count=16,
                )
            except aioredis.ResponseError:
                continue
            for entry_id, fields in entries or []:
                await self._handle(redis, topic, entry_id, fields)

    async def _handle(
        self, redis: aioredis.Redis, topic: str, entry_id: str, fields: dict[str, str]
    ) -> None:
        """Run every handler for ``topic``, then ack. Ack only on full success."""
        dedupe_key = f"inbox:{self._service}:{topic}:{entry_id}"
        try:
            first_time = await redis.set(dedupe_key, "1", nx=True, ex=DEDUPE_TTL_SECONDS)
        except Exception:
            first_time = True  # Redis flaky — prefer reprocessing over dropping
        if not first_time:
            await redis.xack(topic, self._service, entry_id)
            return

        try:
            envelope = json.loads(fields.get("payload") or "{}")
        except ValueError:
            log.error("Undecodable event %s on %s — quarantining", entry_id, topic)
            await self._quarantine(redis, topic, entry_id, fields)
            return
        data = envelope.get("data", {}) if isinstance(envelope, dict) else {}
        # Handlers see the event id so they can persist it for their own
        # idempotency checks (see analytics / notifications).
        if isinstance(data, dict):
            data.setdefault("_event_id", entry_id)

        try:
            for handler in self._handlers.get(topic, []):
                await handler(data, topic)
        except Exception as exc:
            log.exception("Handler for %s failed on %s: %s", topic, entry_id, exc)
            # Roll back the marker so the redelivery is allowed to retry.
            with contextlib.suppress(Exception):
                await redis.delete(dedupe_key)
            if await self._attempts_exhausted(redis, topic, entry_id):
                await self._quarantine(redis, topic, entry_id, fields)
            return  # leave pending → reclaimed later

        await redis.xack(topic, self._service, entry_id)

    async def _attempts_exhausted(
        self, redis: aioredis.Redis, topic: str, entry_id: str
    ) -> bool:
        try:
            pending = await redis.xpending_range(
                topic, self._service, min=entry_id, max=entry_id, count=1
            )
        except Exception:
            return False
        return bool(pending) and pending[0].get("times_delivered", 0) >= self._max_attempts

    async def _quarantine(
        self, redis: aioredis.Redis, topic: str, entry_id: str, fields: dict[str, str]
    ) -> None:
        """Park an unprocessable event so it stops blocking the stream."""
        with contextlib.suppress(Exception):
            await redis.xadd(
                f"{topic}:dead",
                {**fields, "original_id": entry_id, "consumer_group": self._service},
                maxlen=1_000,
                approximate=True,
            )
        with contextlib.suppress(Exception):
            await redis.xack(topic, self._service, entry_id)
        log.error("Event %s on %s quarantined to %s:dead", entry_id, topic, topic)

    # ------------------------------ Lifecycle ----------------------------

    async def stop(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._redis is not None:
            with contextlib.suppress(Exception):
                await self._redis.aclose()
            self._redis = None
