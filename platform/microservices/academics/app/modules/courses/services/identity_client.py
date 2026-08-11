"""Look up platform admins — used to auto-connect a newly enrolled student
with staff in chat, alongside their teacher (see services/chat_client.py).
Best-effort: forwards the enrolling admin's own token (they already have
permission to list admins by definition), swallows failures.
"""

from __future__ import annotations

import logging

from edubridge_shared.clients import ServiceClient, ServiceError, service_url

log = logging.getLogger("courses")

_identity = ServiceClient(service_url("auth"))


async def super_admin_ids(token: str) -> list[str]:
    try:
        users = await _identity.get("/auth/admin/users?role=super_admin", token=token)
    except ServiceError as exc:
        log.warning("Could not list super admins: %s", exc)
        return []
    return [u["id"] for u in users]
