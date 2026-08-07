"""Auth dependencies for the tutors module (department-wide)."""

from __future__ import annotations

from ....deps import get_current_user, require_roles

__all__ = ["get_current_user", "require_roles"]
