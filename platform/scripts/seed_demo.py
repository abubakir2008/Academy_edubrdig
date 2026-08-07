"""Seed demo data so the platform looks alive for a colleague demo.

Creates a demo student, several tutors with rich profiles, and runs one full
lesson flow (book -> confirm -> pay -> complete -> review) so a tutor shows real
earnings + rating. Safe to re-run (existing accounts are reused).

There is no self-registration anymore — accounts are created through
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
import time
import uuid
from datetime import datetime, timedelta, timezone

import requests

DIRECT = os.getenv("DIRECT") == "1"
BASE = os.getenv("BASE_URL", "http://localhost/api")
PORT = os.getenv("SERVICE_PORT", "8000")
S = requests.Session()

DEMO_PASSWORD = "demo1234"

# Each department container serves several of the original route prefixes —
# see platform/deploy/docker/traefik/dynamic.yml for the authoritative map.
PREFIX_DEPARTMENT = {
    "auth": "identity", "users": "identity",
    "tutors": "catalog", "students": "catalog", "search": "catalog",
    "booking": "scheduling", "calendar": "scheduling", "lessons": "scheduling", "video": "scheduling",
    "payments": "finance", "wallet": "finance",
    "chat": "engagement", "notifications": "engagement", "reviews": "engagement", "support": "engagement",
    "cms": "content", "localization": "content", "ai": "content", "storage": "content",
    "admin": "backoffice", "moderation": "backoffice", "analytics": "backoffice",
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


TUTORS = [
    dict(email="anna.eng@edubridge-demo.com", name="Anna Smith", headline="Certified English tutor (IELTS/TOEFL)",
         country="GB", native="english", langs=["english"], specs=["english"], exp=8, price=2000, trial=500),
    dict(email="ivan.math@edubridge-demo.com", name="Ivan Petrov", headline="Mathematics & Physics for school and exams",
         country="RU", native="russian", langs=["russian", "english"], specs=["mathematics", "physics"],
         exp=12, price=1500, trial=0),
    dict(email="mei.chi@edubridge-demo.com", name="Mei Chen", headline="Native Chinese conversation & HSK prep",
         country="CN", native="chinese", langs=["chinese", "english"], specs=["chinese"], exp=5, price=1800, trial=400),
    dict(email="carlos.es@edubridge-demo.com", name="Carlos Ruiz", headline="Spanish for beginners and travelers",
         country="ES", native="spanish", langs=["spanish"], specs=["spanish"], exp=6, price=1200, trial=300),
    dict(email="dev.it@edubridge-demo.com", name="Dilnoza K.", headline="Backend development: Python, FastAPI, SQL",
         country="KG", native="russian", langs=["russian", "english"], specs=["backend development"],
         exp=4, price=2500, trial=0),
    dict(email="aigerim.de@edubridge-demo.com", name="Aigerim T.", headline="German A1-B2, exam preparation",
         country="KG", native="kyrgyz", langs=["german", "russian"], specs=["german"], exp=7, price=1600, trial=350),
]


def seed_tutor(t: dict, admin_token: str) -> str:
    token = ensure_account(t["email"], "tutor", t["name"], admin_token)
    req("PUT", "/users/me", token, json={"full_name": t["name"], "country": t["country"]})
    req("POST", "/tutors/me", token, json={
        "headline": t["headline"], "description": f"{t['name']} — {t['exp']} years of experience.",
        "country": t["country"], "native_language": t["native"],
        "languages_taught": t["langs"], "specializations": t["specs"],
        "experience_years": t["exp"], "price_cents": t["price"],
        "trial_price_cents": (t["trial"] or None), "currency": "USD", "is_active": True,
    })
    req("PUT", "/tutors/me/working-hours", token, json=[
        {"weekday": d, "start_time": "09:00:00", "end_time": "18:00:00"} for d in range(5)
    ])
    return token


def main():
    print(f"Seeding demo data via {'DIRECT' if DIRECT else BASE} ...")
    admin_token = admin_login()

    student = ensure_account("demo@edubridge-demo.com", "student", "Demo Student", admin_token)
    req("PUT", "/users/me", student, json={"full_name": "Demo Student", "country": "KG",
                                            "languages": ["russian", "english"], "timezone": "Asia/Bishkek"})
    student_id = req("GET", "/auth/me", student).json()["id"]

    tutor_tokens = {}
    for t in TUTORS:
        tutor_tokens[t["email"]] = seed_tutor(t, admin_token)
        print("  tutor:", t["email"])

    # One full flow so Anna has a lesson, earnings and a rating.
    anna = tutor_tokens[TUTORS[0]["email"]]
    anna_id = req("GET", "/auth/me", anna).json()["id"]
    start = (datetime.now(tz=timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    b = req("POST", "/booking", student, json={
        "tutor_id": anna_id, "scheduled_start": start.isoformat(), "duration_minutes": 60, "is_trial": False,
    })
    if b.status_code == 201:
        booking_id = b.json()["id"]
        req("POST", f"/booking/{booking_id}/confirm", anna)
        req("POST", "/payments/checkout", student, json={"booking_id": booking_id})
        time.sleep(4)  # let events create the lesson + credit the wallet
        lessons = req("GET", "/lessons/me", anna).json()
        if isinstance(lessons, list) and lessons:
            lid = lessons[0]["id"]
            req("POST", f"/lessons/{lid}/complete", anna)
            req("POST", "/reviews", student, json={
                "tutor_id": anna_id, "lesson_id": lid, "rating": 5,
                "comment": "Excellent lesson, very clear explanations!",
            })
        print("  ran one full lesson flow for Anna (earnings + rating)")

    print(
        "\nDone. student/tutor passwords were randomly generated on creation — "
        "reset one via POST /auth/admin/users/<id>/reset-password if you need to log in as it."
    )
    print("  student: demo@edubridge-demo.com")
    for t in TUTORS:
        print("  tutor:  ", t["email"])


if __name__ == "__main__":
    main()
