"""FastAPI dependencies for verifying JWTs in *any* service.

Every downstream service (users, tutors, booking, ...) uses these helpers to
authenticate requests without re-implementing token parsing. Import lazily so
the shared package can still be used in non-FastAPI contexts.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .roles import Role
from .security import ACCESS_TOKEN_TYPE, TokenError, TokenPayload, decode_token

_bearer = HTTPBearer(auto_error=True)


class CurrentUser:
    """Lightweight authenticated principal extracted from an access token."""

    def __init__(self, user_id: str, role: str) -> None:
        self.id = user_id
        self.role = role

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"CurrentUser(id={self.id!r}, role={self.role!r})"


def build_auth_dependencies(*, secret_key: str, algorithm: str):
    """Return ``(get_current_user, require_roles)`` bound to a service's config."""

    def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    ) -> CurrentUser:
        try:
            payload: TokenPayload = decode_token(
                credentials.credentials,
                secret_key=secret_key,
                algorithm=algorithm,
                expected_type=ACCESS_TOKEN_TYPE,
            )
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        return CurrentUser(user_id=payload.sub, role=payload.role)

    def require_roles(*allowed: Role | str):
        allowed_values = {r.value if isinstance(r, Role) else r for r in allowed}

        def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
            if user.role not in allowed_values:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
            return user

        return _dep

    return get_current_user, require_roles


def has_any_role(role: str, allowed: Iterable[Role | str]) -> bool:
    return role in {r.value if isinstance(r, Role) else r for r in allowed}
