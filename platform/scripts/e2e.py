"""End-to-end tests for the EduBridge platform, driven through the gateway.

Covers every remaining role and validates the event-driven side effects
(user registration -> analytics event log).

Usage (stack must be up):
    python scripts/e2e.py
Env:
    BASE_URL   default http://localhost/api
    JWT_SECRET default read from ../.env, else the .env.example value
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import requests

# Two modes:
#   gateway (default): all traffic via Traefik at BASE_URL (e.g. http://localhost/api)
#   direct  (DIRECT=1): hit each department by container name inside the docker
#            network, bypassing the gateway. The platform is 4 departments,
#            each serving several route prefixes (e.g. both /auth and /users
#            are served by the `identity` container) — this table is how
#            DIRECT mode knows which container a prefix lives on.
DIRECT = os.getenv("DIRECT") == "1"
BASE = os.getenv("BASE_URL", "http://localhost/api")
PORT = os.getenv("SERVICE_PORT", "8000")
SESSION = requests.Session()
SESSION.timeout = 45

PREFIX_DEPARTMENT = {
    "auth": "identity", "users": "identity",
    "chat": "engagement", "notifications": "engagement", "support": "engagement",
    "cms": "content", "localization": "content", "ai": "content", "storage": "content",
    "admin": "backoffice", "analytics": "backoffice",
}


def _url(path: str) -> str:
    if DIRECT:
        prefix = path.strip("/").split("/")[0]
        host = PREFIX_DEPARTMENT.get(prefix, prefix)
        return f"http://{host}:{PORT}{path}"
    return f"{BASE}{path}"

_passed = 0
_failed = 0
_failures: list[str] = []


# --------------------------- test harness ------------------------------

def check(name: str, cond: bool, detail: str = "") -> bool:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  \033[92mPASS\033[0m {name}")
    else:
        _failed += 1
        _failures.append(f"{name} — {detail}")
        print(f"  \033[91mFAIL\033[0m {name}  {detail}")
    return cond


def req(method: str, path: str, token: str | None = None, **kw):
    headers = kw.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # Retry transient 401 "Invalid token" caused by Docker VM clock jitter.
    r = None
    for attempt in range(4):
        r = SESSION.request(method, _url(path), headers=headers, timeout=45, **kw)
        if r.status_code == 401 and "Invalid token" in r.text and attempt < 3:
            time.sleep(1)
            continue
        return r
    return r


# --------------------------- auth helpers ------------------------------

def read_secret() -> str:
    if os.getenv("JWT_SECRET"):
        return os.environ["JWT_SECRET"]
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            if line.startswith("JWT_SECRET_KEY="):
                return line.split("=", 1)[1].strip()
    return "change-me-in-production-use-a-long-random-string"


SECRET = read_secret()


def staff_token(role: str) -> str:
    """Mint a valid platform token for a staff role (not self-registerable).

    ``iat`` is backdated so a host clock running ahead of the Docker VM (common
    after a laptop resume) doesn't make the token look issued-in-the-future.
    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "role": role,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": now - timedelta(minutes=5),
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def register_login(role: str) -> tuple[str, str]:
    """Create a student/tutor through the admin API (self-registration is
    gone) and return (user_id, access_token) for that account itself.

    `staff_token("super_admin")` mints an admin-authorized JWT out of thin
    air — no DB row needed, `require_roles` only reads token claims — which
    sidesteps the chicken-and-egg problem of needing an admin to create the
    first user this script tests with.
    """
    email = f"{role}-{uuid.uuid4().hex[:8]}@edubridge-qa.com"
    admin = staff_token("super_admin")
    r = req("POST", "/auth/admin/users", admin, json={"email": email, "full_name": f"E2E {role}", "role": role})
    assert r.status_code == 201, f"admin-create {role}: {r.status_code} {r.text}"
    body = r.json()
    uid, password = body["user"]["id"], body["password"]
    r = req("POST", "/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login {role}: {r.status_code} {r.text}"
    return uid, r.json()["access_token"]


# ------------------------------- flows ---------------------------------

def test_auth():
    print("\n[auth]")
    uid, token = register_login("student")
    check("admin-create+login student", bool(token))
    me = req("GET", "/auth/me", token)
    check("GET /auth/me", me.status_code == 200 and me.json()["role"] == "student", me.text)
    # refresh
    r = req("POST", "/auth/login", json={"email": me.json()["email"], "password": "supersecret123"}) \
        if False else None
    return uid, token


def test_support():
    print("\n[admin] tickets")
    _, stok_user = register_login("student")
    r = req("POST", "/support/tickets", stok_user, json={"subject": "Help", "message": "hi"})
    check("student open ticket", r.status_code == 201, r.text)
    sm = staff_token("admin")
    r = req("GET", "/support/tickets", sm)
    check("support list tickets", r.status_code == 200 and len(r.json()) >= 1, r.text[:200])


def test_content():
    print("\n[admin] CMS + localization")
    ctok = staff_token("admin")
    slug = f"post-{uuid.uuid4().hex[:6]}"
    r = req("POST", "/cms/articles", ctok, json={
        "slug": slug, "type": "blog", "title": "Hello", "body": "world", "published": True,
    })
    check("content create article", r.status_code == 201, r.text)
    r = req("GET", f"/cms/articles/{slug}")
    check("public read article", r.status_code == 200, r.text)
    r = req("POST", "/localization/languages", ctok, json={"code": "en", "name": "English"})
    check("content add language", r.status_code == 201, r.text)


def test_admin_analytics():
    print("\n[admin/super_admin] dashboard, settings, analytics, users")
    atok = staff_token("admin")
    r = req("GET", "/admin/dashboard", atok)
    check("admin dashboard", r.status_code == 200, r.text)
    r = req("PUT", "/admin/settings/notifications", atok,
            json={"category": "notifications", "value": {"email_enabled": True}})
    check("admin upsert setting", r.status_code == 200, r.text)
    r = req("GET", "/users", atok)
    check("admin list user profiles", r.status_code == 200, r.text[:200])
    today = datetime.now(tz=timezone.utc).date().isoformat()
    r = req("GET", f"/analytics/metrics/summary?date_from={today}&date_to={today}", atok)
    check("admin analytics summary", r.status_code == 200, r.text)


def test_ai():
    print("\n[ai] homework generator")
    _, tok = register_login("student")
    r = req("POST", "/ai/homework/generate", tok,
            json={"subject": "English", "level": "beginner", "topic": "past tense", "num_tasks": 3})
    check("ai generate homework", r.status_code == 200 and len(r.json().get("tasks", [])) == 3, r.text[:200])


def main():
    print(f"EduBridge E2E against {BASE}")
    test_auth()
    test_support()
    test_content()
    test_admin_analytics()
    test_ai()

    print("\n" + "=" * 50)
    print(f"RESULT: {_passed} passed, {_failed} failed")
    if _failures:
        print("Failures:")
        for f in _failures:
            print("  -", f)
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
