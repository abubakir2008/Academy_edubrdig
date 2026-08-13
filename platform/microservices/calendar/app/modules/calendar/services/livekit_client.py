"""LiveKit room access — replaces the old per-tutor Zoom OAuth integration.

Nobody links an account and nothing is created ahead of time: a LiveKit
access token is a self-signed JWT (signed with the platform's own
`LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET`), minted entirely in-process with no
outbound network call. The room itself isn't a row in any database — it's
just a name (`lesson-<id>`) that starts existing the moment the first
token-holder connects and stops existing once everyone leaves, so there is
nothing to create, update or delete when a lesson is scheduled, rescheduled
or removed.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from livekit import api as lk_api

from ..core.config import get_settings

_settings = get_settings()

#: How long a join token stays valid once issued — comfortably longer than
#: any single lesson, so nobody gets disconnected mid-call.
_TOKEN_TTL = timedelta(hours=6)


class LiveKitError(Exception):
    pass


def is_configured() -> bool:
    return bool(_settings.livekit_url and _settings.livekit_api_key and _settings.livekit_api_secret)


def room_name(lesson_id: uuid.UUID) -> str:
    return f"lesson-{lesson_id}"


def mint_token(*, lesson_id: uuid.UUID, identity: str, name: str) -> str:
    """A token scoped to exactly this lesson's room. Every participant
    (teacher and student alike) gets equal publish/subscribe rights — there's
    no "host" concept for a 1:1 lesson call the way Zoom had one."""
    if not is_configured():
        raise LiveKitError("LiveKit is not configured on this server")
    grants = lk_api.VideoGrants(room_join=True, room=room_name(lesson_id), can_publish=True, can_subscribe=True)
    token = (
        lk_api.AccessToken(_settings.livekit_api_key, _settings.livekit_api_secret)
        .with_identity(identity)
        .with_name(name)
        .with_grants(grants)
        .with_ttl(_TOKEN_TTL)
    )
    return token.to_jwt()
