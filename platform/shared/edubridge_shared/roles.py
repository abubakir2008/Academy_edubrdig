"""Platform-wide user roles.

Kept in the shared library so every service agrees on the exact string values
that appear inside JWT claims and in each service database.
"""

from enum import Enum


class Role(str, Enum):
    STUDENT = "student"
    TUTOR = "tutor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    MODERATOR = "moderator"
    SUPPORT_MANAGER = "support_manager"
    FINANCE_MANAGER = "finance_manager"
    CONTENT_MANAGER = "content_manager"


# Roles that grant access to the admin panel / privileged operations.
STAFF_ROLES: frozenset[Role] = frozenset(
    {
        Role.ADMIN,
        Role.SUPER_ADMIN,
        Role.MODERATOR,
        Role.SUPPORT_MANAGER,
        Role.FINANCE_MANAGER,
        Role.CONTENT_MANAGER,
    }
)
