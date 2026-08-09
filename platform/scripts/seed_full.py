"""Seed a full demo dataset: one account per staff role, plus a demo student.

There is no self-registration anymore (see POST /auth/admin/users) — every
account here is admin-created. `admin@edubridge-demo.com` itself has no
"admin" to be created by, though, so it's the one exception: this script
still writes it (and the other four staff accounts) directly into the
identity department's database, using the same password hashing the app
itself uses. Once that account exists, everything else (the demo student)
goes through the real `/auth/admin/users` API, logged in as that admin — see
`ensure_account()`.

Run through the gateway:   python scripts/seed_full.py
Run inside the network:    DIRECT=1 python scripts/seed_full.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

DIRECT = os.getenv("DIRECT") == "1"
BASE = os.getenv("BASE_URL", "http://localhost/api")
PORT = os.getenv("SERVICE_PORT", "8000")

if "--staff-only" not in sys.argv:
    # Deferred: `--staff-only` runs inside the identity container, whose image
    # only has httpx installed, not requests — it never needs this branch.
    import requests

    S = requests.Session()

DEMO_PASSWORD = "demo1234"

PREFIX_DEPARTMENT = {
    "auth": "identity", "users": "identity",
    "chat": "engagement", "notifications": "engagement", "support": "engagement",
    "cms": "content", "localization": "content", "ai": "content", "storage": "content",
    "admin": "backoffice", "analytics": "backoffice",
}

REGISTERED_EMAILS_FILE = None  # set in main() once ROOT is known


def url(path: str) -> str:
    if DIRECT:
        prefix = path.strip("/").split("/")[0]
        host = PREFIX_DEPARTMENT.get(prefix, prefix)
        return f"http://{host}:{PORT}{path}"
    return f"{BASE}{path}"


def req(method, path, token=None, **kw):
    h = kw.pop("headers", {})
    if token:
        h["Authorization"] = f"Bearer {token}"
    # Retried: this host's Docker networking occasionally stalls a request
    # for no server-side reason (confirmed against these same endpoints via
    # scripts/e2e.py, which passes clean) — a transient host quirk, not
    # something to work around in the application.
    last_exc = None
    for attempt in range(4):
        try:
            return S.request(method, url(path), headers=h, timeout=30, **kw)
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            print(f"    (retry {attempt+1}/4 after {exc.__class__.__name__} on {method} {path})")
    raise last_exc


def login(email: str, password: str) -> str:
    r = req("POST", "/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def ensure_account(email: str, role: str, full_name: str, admin_token: str) -> tuple[str, str]:
    """Create the account through the admin API (self-registration is gone);
    if it already exists from a previous run, rotate its password instead —
    that's the only way to recover a usable login for it. Returns
    (access_token, password actually used) so callers can print it if it's
    the kind of account someone might want to log into by hand."""
    create = req("POST", "/auth/admin/users", admin_token,
                 json={"email": email, "full_name": full_name, "role": role})
    if create.status_code == 201:
        password = create.json()["password"]
    else:
        existing = req("GET", "/auth/admin/users", admin_token, params={"role": role})
        existing.raise_for_status()
        match = next(u for u in existing.json() if u["email"] == email)
        reset = req("POST", f"/auth/admin/users/{match['id']}/reset-password", admin_token)
        reset.raise_for_status()
        password = reset.json()["password"]
    return login(email, password), password


def whoami(token: str) -> dict:
    r = req("GET", "/auth/me", token)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------------
# Staff accounts: created directly in the identity department's own database,
# using its own password hashing, since there is no API for this.
# --------------------------------------------------------------------------

STAFF_ACCOUNTS = [
    ("admin@edubridge-demo.com", "super_admin", "Demo Super Admin"),
    ("moderator@edubridge-demo.com", "moderator", "Demo Moderator"),
]


async def _create_staff_accounts_in_db() -> None:
    """Runs inside the identity department's own container (see main()), so it
    can import the app's real password hashing and User model directly.
    """
    sys.path.insert(0, "/app/microservices/identity")
    from app.db.session import SessionLocal  # noqa: E402
    from app.modules.auth.core.security import hash_password  # noqa: E402
    from app.modules.auth.models.user import User  # noqa: E402
    from sqlalchemy import select  # noqa: E402

    async with SessionLocal() as db:
        for email, role, full_name in STAFF_ACCOUNTS:
            existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if existing is not None:
                print(f"  staff account already exists: {email} ({role})")
                continue
            user = User(
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=full_name,
                role=role,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            print(f"  created staff account: {email} ({role})")


def create_staff_accounts() -> None:
    """Runs the DB-side creation via `docker exec` into the identity
    container — the calling process (this script) may be running on the host
    or inside an unrelated container, neither of which has the identity
    department's code or its database credentials/network route.

    Requires the `docker` CLI on whatever host runs *this* function — that's
    the machine with the compose project, not necessarily wherever the rest
    of this script's HTTP calls originate. If it's unavailable (e.g. this
    script itself is running inside a plain python container without the
    Docker CLI), run `docker exec platform-identity-1 python /tmp/seed_full.py
    --staff-only` (after `docker cp`'ing this file there) from the real host
    once, then re-run the rest of this script — it's idempotent and will
    just log in with the accounts that already exist.
    """
    import subprocess

    # Simplest reliable path: copy this module into the identity container and
    # invoke its own async helper there, rather than trying to reproduce the
    # import machinery inline on the command line.
    here = Path(__file__).resolve()
    try:
        subprocess.run(
            ["docker", "cp", str(here), "platform-identity-1:/tmp/seed_full.py"],
            check=True,
        )
    except FileNotFoundError:
        print(
            "  docker CLI not available here — skipping staff account creation.\n"
            "  Run this once from the real Docker host, then re-run this script:\n"
            "    docker cp scripts/seed_full.py platform-identity-1:/tmp/seed_full.py\n"
            "    docker exec platform-identity-1 python /tmp/seed_full.py --staff-only"
        )
        return
    result = subprocess.run(
        ["docker", "exec", "platform-identity-1", "python", "/tmp/seed_full.py", "--staff-only"],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit("staff account creation failed")


def main() -> None:
    print(f"Seeding full demo dataset via {'DIRECT' if DIRECT else BASE} ...")

    print("\n[staff accounts]")
    create_staff_accounts()
    admin_token = login("admin@edubridge-demo.com", DEMO_PASSWORD)

    print("\n[student]")
    student, student_password = ensure_account(
        "student@edubridge-demo.com", "student", "Demo Student", admin_token
    )
    req("PUT", "/users/me", student, json={
        "full_name": "Demo Student", "country": "KG",
        "languages": ["russian", "english"], "timezone": "Asia/Bishkek",
    })
    print(f"  student@edubridge-demo.com (password: {student_password})")

    print("\n" + "=" * 60)
    print("Done.")
    print("\nStaff logins (password: demo1234):")
    for email, role, _ in STAFF_ACCOUNTS:
        print(f"  {role:18s} {email}")
    print(f"\n  {'student':18s} student@edubridge-demo.com  (password: {student_password})")


async def _run() -> None:
    await _create_staff_accounts_in_db()


if __name__ == "__main__":
    if "--staff-only" in sys.argv:
        asyncio.run(_run())
    else:
        main()
