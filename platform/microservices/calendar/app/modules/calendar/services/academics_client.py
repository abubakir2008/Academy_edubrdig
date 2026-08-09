"""Synchronous lookups against the academics department (course ownership).

Scheduling a lesson needs an authoritative, right-now answer to "does this
course exist, and is this tutor really its teacher?" — that can't wait for
an event to fan out, so it's one of the few places in the platform that uses
``edubridge_shared.clients.ServiceClient`` for real. The caller's own JWT is
forwarded rather than a shared service credential, so academics' normal
per-user authorization (`/courses/{id}` 403s a tutor who isn't the teacher,
404s a course that doesn't exist) does the actual checking — this module is
just plumbing.
"""

from __future__ import annotations

import uuid

from edubridge_shared.clients import ServiceClient, ServiceError, service_url

_academics = ServiceClient(service_url("courses"))

__all__ = ["ServiceError", "get_course", "my_course_ids"]


async def get_course(course_id: uuid.UUID, token: str) -> dict:
    """Raises ServiceError(404) if the course doesn't exist, (403) if the
    caller isn't allowed to see it (mirrors academics' own rules)."""
    return await _academics.get(f"/courses/{course_id}", token=token)


async def my_course_ids(token: str) -> list[uuid.UUID]:
    """Course ids the caller can see via `/courses/me` — teacher for a
    tutor, enrolled-in for a student. Used to scope a student's lesson feed
    without calendar needing its own copy of any course roster."""
    courses = await _academics.get("/courses/me", token=token)
    return [uuid.UUID(c["id"]) for c in courses]
