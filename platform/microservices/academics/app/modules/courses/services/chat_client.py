"""Best-effort: auto-create a chat conversation between two users.

So a newly enrolled student can reach their teacher and platform admins
immediately, without either side having to start the chat manually first.
Calls engagement's internal-only endpoint (no user token — just the shared
X-Internal-Secret, see edubridge_shared.clients.require_internal). This is
a courtesy, not something enrollment should ever fail over, so any failure
is logged and swallowed.
"""

from __future__ import annotations

import logging

from edubridge_shared.clients import ServiceClient, ServiceError, service_url

log = logging.getLogger("courses")

_chat = ServiceClient(service_url("chat"))


async def ensure_conversation(user_a: str, user_b: str) -> None:
    try:
        await _chat.post("/chat/conversations/internal", {"user_a": user_a, "user_b": user_b})
    except ServiceError as exc:
        log.warning("Could not auto-create chat conversation between %s and %s: %s", user_a, user_b, exc)
