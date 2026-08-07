"""End-to-end tests for the EduBridge platform, driven through the gateway.

Covers every role and validates the event-driven side effects (payment ->
wallet credit, booking confirm -> lesson auto-create, review -> rating update,
verification -> is_verified).

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
#            network, bypassing the gateway. The platform is 7 departments,
#            each serving several of the original route prefixes (e.g. both
#            /auth and /users are served by the `identity` container) — this
#            table is how DIRECT mode knows which container a prefix lives on.
DIRECT = os.getenv("DIRECT") == "1"
BASE = os.getenv("BASE_URL", "http://localhost/api")
PORT = os.getenv("SERVICE_PORT", "8000")
SESSION = requests.Session()
SESSION.timeout = 45

PREFIX_DEPARTMENT = {
    "auth": "identity", "users": "identity",
    "tutors": "catalog", "students": "catalog", "search": "catalog",
    "booking": "scheduling", "calendar": "scheduling", "lessons": "scheduling", "video": "scheduling",
    "payments": "finance", "wallet": "finance",
    "chat": "engagement", "notifications": "engagement", "reviews": "engagement", "support": "engagement",
    "cms": "content", "localization": "content", "ai": "content", "storage": "content",
    "admin": "backoffice", "moderation": "backoffice", "analytics": "backoffice",
}


def _next_weekday_at(weekday: int, hour: int) -> datetime:
    """The next occurrence of ``weekday`` (0=Mon) at ``hour``:00 UTC, strictly
    in the future. Booking now enforces the tutor's calendar (see
    calendar/crud/calendar.py::is_available), so a booking test has to land
    inside the availability rule the test itself just configured — "tomorrow,
    whatever weekday that happens to be" isn't good enough anymore."""
    now = datetime.now(tz=timezone.utc)
    days_ahead = (weekday - now.weekday()) % 7
    days_ahead = days_ahead if days_ahead > 0 else 7  # never today
    return (now + timedelta(days=days_ahead)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )


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


def poll(fn, ok, tries=20, delay=1.5):
    """Retry fn() until ok(result) or attempts run out (for async event effects)."""
    last = None
    for _ in range(tries):
        try:
            last = fn()
            if ok(last):
                return last
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(delay)
    return last


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


def test_tutor_setup():
    print("\n[tutor] profile + availability")
    uid, token = register_login("tutor")
    r = req("POST", "/tutors/me", token, json={
        "headline": "Expert English tutor", "description": "10y experience",
        "country": "GB", "native_language": "english",
        "languages_taught": ["english"], "specializations": ["english"],
        "experience_years": 10, "price_cents": 2000, "trial_price_cents": 500,
        "currency": "USD", "is_active": True,
    })
    check("tutor create profile", r.status_code in (200, 201), r.text)
    r = req("PUT", "/tutors/me/working-hours", token, json=[
        {"weekday": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
    ])
    check("tutor set working hours", r.status_code == 200, r.text)
    r = req("PUT", "/calendar/me/rules", token, json=[
        {"weekday": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
    ])
    check("tutor set calendar rules", r.status_code == 200, r.text)
    # public browse should list this tutor. limit=200: this suite (and
    # scripts/seed_full.py) may have left many prior English tutors in a
    # long-lived dev database, all tied at rating=0 — a small default page
    # size would make this a pagination test by accident.
    r = req("GET", "/tutors?language=english&limit=100")  # 100 is the API's own cap
    listed = r.status_code == 200 and any(t["user_id"] == uid for t in r.json())
    check("tutor appears in browse", listed, r.text[:200])
    return uid, token


def test_student_booking_payment(tutor_id: str, tutor_token: str):
    print("\n[student] browse -> favorite -> book -> pay ; [events] wallet+lesson")
    uid, token = register_login("student")
    req("PUT", "/users/me", token, json={"full_name": "Ann", "country": "US",
                                          "languages": ["english"], "timezone": "UTC"})
    r = req("POST", f"/students/me/favorites/{tutor_id}", token)
    check("student add favorite", r.status_code == 201, r.text)

    # Matches the weekday=0 (Monday), 09:00-17:00 UTC rule set in
    # test_tutor_profile() above.
    start = _next_weekday_at(weekday=0, hour=10)
    # Price is NOT sent by the client — the server reads it from the tutor profile.
    r = req("POST", "/booking", token, json={
        "tutor_id": tutor_id, "scheduled_start": start.isoformat(),
        "duration_minutes": 60, "is_trial": False,
    })
    check("student create booking", r.status_code == 201, r.text)
    check("booking price resolved server-side (2000)",
          r.status_code == 201 and r.json().get("price_cents") == 2000, r.text[:200])
    booking_id = r.json().get("id")

    # tutor confirms -> booking.confirmed -> lessons auto-creates a lesson
    r = req("POST", f"/booking/{booking_id}/confirm", tutor_token)
    check("tutor confirm booking", r.status_code == 200, r.text)

    lessons = poll(
        lambda: req("GET", "/lessons/me", tutor_token).json(),
        lambda js: isinstance(js, list) and len(js) >= 1,
    )
    check("EVENT booking.confirmed -> lesson auto-created",
          isinstance(lessons, list) and len(lessons) >= 1,
          f"got {lessons}")
    lesson_id = lessons[0]["id"] if isinstance(lessons, list) and lessons else None

    # student pays (amount comes from the booking) -> payment.succeeded -> wallet credit
    r = req("POST", "/payments/checkout", token, json={"booking_id": booking_id})
    check("student checkout", r.status_code == 201, r.text)
    payment_id = r.json().get("payment_id")
    check("checkout settled (mock)", r.json().get("status") == "succeeded", r.text)
    p = req("GET", f"/payments/{payment_id}", token)
    check("commission split (80% of 2000 = 1600)",
          p.status_code == 200 and p.json().get("tutor_earnings_cents") == 1600, p.text[:200])

    wallet = poll(
        lambda: req("GET", "/wallet/me", tutor_token).json(),
        lambda js: isinstance(js, dict) and js.get("balance_cents", 0) >= 1600,
    )
    check("EVENT payment.succeeded -> wallet credited",
          isinstance(wallet, dict) and wallet.get("balance_cents", 0) >= 1600,
          f"got {wallet}")

    # complete lesson + leave review -> rating updates on tutor
    if lesson_id:
        req("POST", f"/lessons/{lesson_id}/complete", tutor_token)
    r = req("POST", "/reviews", token, json={
        "tutor_id": tutor_id, "lesson_id": lesson_id, "rating": 5, "comment": "Great!",
    })
    check("student leave review", r.status_code == 201, r.text)

    rated = poll(
        lambda: req("GET", f"/tutors/{tutor_id}").json(),
        lambda js: isinstance(js, dict) and js.get("total_reviews", 0) >= 1,
    )
    check("EVENT review.created -> tutor rating updated",
          isinstance(rated, dict) and rated.get("total_reviews", 0) >= 1,
          f"got rating={rated.get('rating') if isinstance(rated, dict) else rated}")
    return uid, token


def test_moderator(tutor_id: str, tutor_token: str):
    print("\n[moderator] verify tutor ; [event] tutor.verified -> is_verified")
    r = req("POST", "/moderation/verification", tutor_token, json={"kind": "profile"})
    check("tutor submit verification", r.status_code == 201, r.text)
    req_id = r.json().get("id")
    mtok = staff_token("moderator")
    r = req("GET", "/moderation/verification?status=pending", mtok)
    check("moderator list verifications", r.status_code == 200, r.text)
    r = req("POST", f"/moderation/verification/{req_id}/review", mtok,
            json={"approve": True, "note": "ok"})
    check("moderator approve", r.status_code == 200, r.text)
    verified = poll(
        lambda: req("GET", f"/tutors/{tutor_id}").json(),
        lambda js: isinstance(js, dict) and js.get("is_verified") is True,
    )
    check("EVENT tutor.verified -> is_verified true",
          isinstance(verified, dict) and verified.get("is_verified") is True,
          f"got {verified.get('is_verified') if isinstance(verified, dict) else verified}")


def test_finance(tutor_token: str):
    print("\n[finance_manager] withdrawal approve")
    r = req("POST", "/wallet/me/withdrawals", tutor_token,
            json={"amount_cents": 500, "method": "bank_card", "destination": "4111 1111 1111 1111"})
    check("tutor request withdrawal", r.status_code == 201, r.text)
    wd_id = r.json().get("id")
    ftok = staff_token("finance_manager")
    r = req("POST", f"/wallet/withdrawals/{wd_id}/approve", ftok)
    check("finance approve withdrawal", r.status_code == 200, r.text)


def test_support():
    print("\n[support_manager] tickets")
    _, stok_user = register_login("student")
    r = req("POST", "/support/tickets", stok_user, json={"subject": "Help", "message": "hi"})
    check("student open ticket", r.status_code == 201, r.text)
    sm = staff_token("support_manager")
    r = req("GET", "/support/tickets", sm)
    check("support list tickets", r.status_code == 200 and len(r.json()) >= 1, r.text[:200])


def test_content():
    print("\n[content_manager] CMS + localization")
    ctok = staff_token("content_manager")
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
    print("\n[admin/super_admin] dashboard, settings, categories, analytics, users")
    atok = staff_token("admin")
    r = req("GET", "/admin/dashboard", atok)
    check("admin dashboard", r.status_code == 200, r.text)
    r = req("PUT", "/admin/settings/payment_gateways", atok,
            json={"category": "payments", "value": {"stripe": True}})
    check("admin upsert setting", r.status_code == 200, r.text)
    r = req("POST", "/admin/categories", atok,
            json={"slug": f"cat-{uuid.uuid4().hex[:6]}", "name": "English", "group": "languages"})
    check("admin create category", r.status_code == 201, r.text)
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
    tutor_id, tutor_token = test_tutor_setup()
    test_student_booking_payment(tutor_id, tutor_token)
    test_moderator(tutor_id, tutor_token)
    test_finance(tutor_token)
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
