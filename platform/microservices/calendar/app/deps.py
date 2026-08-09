"""JWT dependencies for every module in the calendar department."""

from __future__ import annotations

from edubridge_shared.fastapi_auth import build_auth_dependencies

from .core.config import get_settings

_settings = get_settings()
get_current_user, require_roles = build_auth_dependencies(
    secret_key=_settings.jwt_secret_key,
    algorithm=_settings.jwt_algorithm,
)
