"""User profile endpoints (namespaced under /users)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from edubridge_shared.fastapi_auth import CurrentUser
from edubridge_shared.roles import STAFF_ROLES

from ....auth.models.user import User
from ...cache import PROFILE_TTL_SECONDS, cache, profile_key
from ...crud import profile as crud
from ...db.session import get_db
from ...schemas.profile import ProfileOut, ProfileUpdate, TutorDetailOut, TutorOut
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/users", tags=["users"])


async def _name_fallback_many(db: AsyncSession, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str | None]:
    """`Profile.full_name` is only ever set once someone visits Settings and
    saves it — most accounts (anyone admin-created, which is everyone on
    this platform) never do. Fall back to the name given at account creation
    (`auth.User.full_name`, in the same department's own `auth` schema) so
    e.g. chat peers don't show up as a raw UUID. Batched: a single
    `WHERE id IN (...)` instead of one query per id."""
    if not user_ids:
        return {}
    result = await db.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
    return dict(result.all())


async def _name_fallback(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    return (await _name_fallback_many(db, [user_id])).get(user_id)


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    profile = await crud.get_or_create(db, uuid.UUID(user.id))
    return ProfileOut.model_validate(profile)


@router.put("/me", response_model=ProfileOut)
async def update_my_profile(
    payload: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    profile = await crud.get_or_create(db, uuid.UUID(user.id))
    data = payload.model_dump(exclude_unset=True)
    profile = await crud.update(db, profile, data)
    await cache.delete(profile_key(user.id))
    return ProfileOut.model_validate(profile)


_MAX_BATCH_IDS = 200


@router.get("/batch", response_model=list[ProfileOut])
async def get_profiles_batch(
    ids: str = Query(..., description="Comma-separated user ids"),
    db: AsyncSession = Depends(get_db),
) -> list[ProfileOut]:
    """Resolve a list of user ids to display names/avatars in one round trip
    — a tutor's roster across several courses, chat peer names, etc. —
    instead of one GET /users/{id} per id. Same public access and
    fallback-to-account-name behaviour as the single-id route below; ids with
    no profile row and no auth account at all are silently omitted rather
    than failing the whole batch. Registered before /{user_id} so the
    literal path "batch" doesn't get swallowed by that route's UUID param.
    """
    try:
        requested = [uuid.UUID(raw) for raw in ids.split(",") if raw.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid id in ids") from exc
    if not requested:
        return []
    if len(requested) > _MAX_BATCH_IDS:
        raise HTTPException(status_code=400, detail=f"Too many ids (max {_MAX_BATCH_IDS})")

    # 90s cache-aside per id: the same handful of names (course rosters, chat
    # peers) gets resolved over and over by different callers, and profile
    # data changes only when someone visits Settings — cheap to serve stale
    # for a minute and a half, invalidated immediately on PUT /users/me.
    out_by_id: dict[uuid.UUID, ProfileOut] = {}
    uncached: list[uuid.UUID] = []
    for uid in requested:
        cached = await cache.get(profile_key(uid))
        if cached is not None:
            out_by_id[uid] = ProfileOut.model_validate(cached)
        else:
            uncached.append(uid)

    if uncached:
        profiles = {p.user_id: p for p in await crud.get_many(db, uncached)}
        need_fallback = [uid for uid in uncached if uid not in profiles or not profiles[uid].full_name]
        fallback_names = await _name_fallback_many(db, need_fallback)

        now = datetime.now(tz=timezone.utc)
        for uid in uncached:
            profile = profiles.get(uid)
            if profile is not None:
                if not profile.full_name:
                    profile.full_name = fallback_names.get(uid)
                result = ProfileOut.model_validate(profile)
            else:
                name = fallback_names.get(uid)
                if name is None:
                    continue  # no profile row and no auth account either — skip
                result = ProfileOut(user_id=uid, full_name=name, avatar_url=None, created_at=now, updated_at=now)
            out_by_id[uid] = result
            await cache.set(profile_key(uid), result.model_dump(mode="json"), PROFILE_TTL_SECONDS)

    return [out_by_id[uid] for uid in requested if uid in out_by_id]


@router.get("/tutors", response_model=list[TutorOut])
async def list_tutors(
    category_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[TutorOut]:
    """Public tutor listing — no auth. `full_name` falls back to the account
    name the same way GET /{user_id} does, so a tutor who never opened
    Settings still shows up with a real name instead of blank."""
    profiles = await crud.list_tutors(db, category_id)
    need_fallback = [p.user_id for p in profiles if not p.full_name]
    fallback_names = await _name_fallback_many(db, need_fallback)
    out = []
    for p in profiles:
        item = TutorOut.model_validate(p)
        if not item.full_name:
            item.full_name = fallback_names.get(p.user_id)
        out.append(item)
    return out


@router.get("/tutors/{user_id}", response_model=TutorDetailOut)
async def get_tutor(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> TutorDetailOut:
    profile = await crud.get_tutor(db, user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tutor not found")
    item = TutorDetailOut.model_validate(profile)
    if not item.full_name:
        item.full_name = await _name_fallback(db, user_id)
    return item


@router.get("/{user_id}", response_model=ProfileOut)
async def get_public_profile(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ProfileOut:
    cached = await cache.get(profile_key(user_id))
    if cached is not None:
        return ProfileOut.model_validate(cached)

    profile = await crud.get(db, user_id)
    if profile is None:
        # No row yet (nobody has ever saved Settings for this account) —
        # still worth answering with the account's given name rather than
        # 404ing, since callers like the chat UI resolve peers through here.
        name = await _name_fallback(db, user_id)
        if name is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
        now = datetime.now(tz=timezone.utc)
        result = ProfileOut(user_id=user_id, full_name=name, avatar_url=None, created_at=now, updated_at=now)
    else:
        if not profile.full_name:
            profile.full_name = await _name_fallback(db, user_id)
        result = ProfileOut.model_validate(profile)

    await cache.set(profile_key(user_id), result.model_dump(mode="json"), PROFILE_TTL_SECONDS)
    return result


@router.get("", response_model=list[ProfileOut])
async def list_profiles(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_roles(*STAFF_ROLES)),
) -> list[ProfileOut]:
    profiles = await crud.list_profiles(db, limit=limit, offset=offset)
    return [ProfileOut.model_validate(p) for p in profiles]
