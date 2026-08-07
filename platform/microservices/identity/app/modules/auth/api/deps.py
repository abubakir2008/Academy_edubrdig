"""Auth dependencies.

Re-exports the department-wide JWT dependencies (``get_current_user`` /
``require_roles``, which only decode the token) and adds
``get_current_db_user``, which additionally loads the actual ``User`` row —
needed by ``/auth/me`` and ``/auth/logout-all``, which return account fields
a bare token claim doesn't carry.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....deps import get_current_user, require_roles
from ..crud import user as crud
from ..db.session import get_db
from ..models.user import User

__all__ = ["get_current_user", "require_roles", "get_current_db_user"]


async def get_current_db_user(
    current=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await crud.get_by_id(db, uuid.UUID(current.id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
