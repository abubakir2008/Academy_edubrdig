"""Bootstrap the first admin/super_admin account on a fresh server.

There is no self-registration and no "promote to staff" endpoint (every
staff account is created by an existing admin via `POST /auth/admin/users`
— see `edubridge_shared`/identity's admin_service.py) — which is fine once
one staff account exists, but leaves no way to create the *first* one
through the API. This script is that one exception: it writes directly
into identity's own database, using the app's own password hashing, the
same way `scripts/seed_full.py --staff-only` does for demo data.

Must run INSIDE the identity container (needs its code + DB credentials).
Use create-admin.sh from the real Docker host instead of calling this
directly — it handles the docker cp + docker exec for you. Manual
equivalent:

    docker cp platform/deploy/scripts/create_admin.py academy_identity:/tmp/create_admin.py
    docker exec -it academy_identity python /tmp/create_admin.py \\
        --email you@example.com --full-name "Your Name" --role super_admin
"""

from __future__ import annotations

import argparse
import asyncio
import secrets
import sys


def generate_password() -> str:
    # Matches edubridge_shared-adjacent admin_service.generate_password()
    # exactly, so a script-created account's password looks like any other
    # admin-created one.
    return secrets.token_urlsafe(9)


async def _create(email: str, full_name: str, role: str, password: str, force: bool) -> None:
    sys.path.insert(0, "/app/microservices/identity")
    from app.db.session import SessionLocal  # noqa: E402
    from app.modules.auth.core.security import hash_password  # noqa: E402
    from app.modules.auth.models.user import User  # noqa: E402
    from edubridge_shared.roles import Role  # noqa: E402
    from sqlalchemy import select  # noqa: E402

    if role not in {r.value for r in Role}:
        raise SystemExit(f"Unknown role {role!r} — choose one of: {', '.join(r.value for r in Role)}")

    async with SessionLocal() as db:
        existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing is not None and not force:
            raise SystemExit(
                f"A user with email {email!r} already exists (role={existing.role}). "
                "Pass --force to overwrite its password and role instead."
            )

        if existing is not None:
            existing.hashed_password = hash_password(password)
            existing.role = role
            existing.full_name = full_name
            existing.is_active = True
            existing.is_verified = True
            await db.commit()
            print(f"Updated existing account: {email} (role={role})")
        else:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                role=role,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            print(f"Created account: {email} (role={role})")

        print(f"Password: {password}")
        print("Log in once and change this password — it's only shown here, this instant.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--role", default="super_admin", choices=["admin", "super_admin", "moderator"])
    parser.add_argument("--password", default=None, help="Omit to auto-generate a random one (recommended).")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing account with this email.")
    args = parser.parse_args()

    password = args.password or generate_password()
    asyncio.run(_create(args.email, args.full_name, args.role, password, args.force))


if __name__ == "__main__":
    main()
