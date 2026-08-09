"""Seed a demo student account so the platform has a non-admin login to demo.

There is no self-registration — accounts are created through
POST /auth/admin/users, logged in as `admin@edubridge-demo.com`. That account
has to already exist (this script doesn't bootstrap it): run
`python scripts/seed_full.py` at least once first, or just
`docker exec platform-identity-1 python /tmp/seed_full.py --staff-only`
(see seed_full.py's `create_staff_accounts()` for the exact steps).

Run through the gateway:   python scripts/seed_demo.py
Run inside the network:    DIRECT=1 python scripts/seed_demo.py   (host = owning department)
"""

from __future__ import annotations

import os

import requests

DIRECT = os.getenv("DIRECT") == "1"
BASE = os.getenv("BASE_URL", "http://localhost/api")
PORT = os.getenv("SERVICE_PORT", "8000")
S = requests.Session()

DEMO_PASSWORD = "demo1234"

# Each department container serves several route prefixes — see
# platform/deploy/docker/traefik/dynamic.yml for the authoritative map.
PREFIX_DEPARTMENT = {
    "auth": "identity", "users": "identity",
    "chat": "engagement", "notifications": "engagement", "support": "engagement",
    "cms": "content", "localization": "content", "ai": "content", "storage": "content",
    "admin": "backoffice", "analytics": "backoffice",
}


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
    return S.request(method, url(path), headers=h, timeout=30, **kw)


def admin_login() -> str:
    r = req("POST", "/auth/login", json={"email": "admin@edubridge-demo.com", "password": DEMO_PASSWORD})
    if not r.ok:
        raise SystemExit(
            "Could not log in as admin@edubridge-demo.com — it doesn't exist yet.\n"
            "Run `python scripts/seed_full.py` (or its --staff-only step) first."
        )
    return r.json()["access_token"]


def ensure_account(email: str, role: str, full_name: str, admin_token: str) -> str:
    """Create through the admin API, or — if it already exists — rotate its
    password, then log in. Returns an access token for the account itself."""
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
    r = req("POST", "/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    print(f"Seeding demo data via {'DIRECT' if DIRECT else BASE} ...")
    admin_token = admin_login()

    student = ensure_account("demo@edubridge-demo.com", "student", "Demo Student", admin_token)
    req("PUT", "/users/me", student, json={"full_name": "Demo Student", "country": "KG",
                                            "languages": ["russian", "english"], "timezone": "Asia/Bishkek"})

    print(
        "\nDone. The student password was randomly generated on creation — "
        "reset it via POST /auth/admin/users/<id>/reset-password if you need to log in as it."
    )
    print("  student: demo@edubridge-demo.com")


if __name__ == "__main__":
    main()
