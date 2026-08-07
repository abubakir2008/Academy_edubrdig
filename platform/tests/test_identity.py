"""Identity department: admin-create / login / refresh / me.

There is no self-registration anymore — every account is created by an
admin via POST /auth/admin/users (see services/admin_service.py). These
tests mint an admin-role JWT directly with `mint_access_token` rather than
going through an actual admin account: `require_roles` only reads token
claims, so no DB row is needed to authorize the admin-only endpoint.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import mint_access_token

pytestmark = pytest.mark.asyncio


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_access_token(str(uuid.uuid4()), 'super_admin')}"}


@pytest.mark.parametrize("department_app", ["identity"], indirect=True)
async def test_admin_create_login_me_roundtrip(department_app):
    _main, client = department_app
    email = f"{uuid.uuid4().hex}@example.com"

    created = await client.post(
        "/auth/admin/users",
        json={"email": email, "full_name": "Ada Lovelace", "role": "student"},
        headers=_admin_headers(),
    )
    assert created.status_code == 201, created.text
    assert created.json()["user"]["email"] == email
    password = created.json()["password"]

    login = await client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    tokens = login.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["access_token"] != tokens["access_token"]


@pytest.mark.parametrize("department_app", ["identity"], indirect=True)
async def test_duplicate_email_is_rejected(department_app):
    _main, client = department_app
    email = f"{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "role": "student"}
    headers = _admin_headers()

    first = await client.post("/auth/admin/users", json=payload, headers=headers)
    assert first.status_code == 201

    second = await client.post("/auth/admin/users", json=payload, headers=headers)
    assert second.status_code == 409


@pytest.mark.parametrize("department_app", ["identity"], indirect=True)
async def test_wrong_password_is_rejected(department_app):
    _main, client = department_app
    email = f"{uuid.uuid4().hex}@example.com"
    await client.post(
        "/auth/admin/users", json={"email": email, "role": "student"}, headers=_admin_headers()
    )

    login = await client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert login.status_code == 401


@pytest.mark.parametrize("department_app", ["identity"], indirect=True)
async def test_reset_password_invalidates_the_old_one(department_app):
    _main, client = department_app
    email = f"{uuid.uuid4().hex}@example.com"
    headers = _admin_headers()

    created = await client.post(
        "/auth/admin/users", json={"email": email, "role": "student"}, headers=headers
    )
    user_id = created.json()["user"]["id"]
    old_password = created.json()["password"]

    reset = await client.post(f"/auth/admin/users/{user_id}/reset-password", headers=headers)
    assert reset.status_code == 200, reset.text
    new_password = reset.json()["password"]
    assert new_password != old_password

    stale = await client.post("/auth/login", json={"email": email, "password": old_password})
    assert stale.status_code == 401

    fresh = await client.post("/auth/login", json={"email": email, "password": new_password})
    assert fresh.status_code == 200


@pytest.mark.parametrize("department_app", ["identity"], indirect=True)
async def test_non_admin_cannot_create_users(department_app):
    _main, client = department_app
    student_headers = {
        "Authorization": f"Bearer {mint_access_token(str(uuid.uuid4()), 'student')}"
    }

    resp = await client.post(
        "/auth/admin/users",
        json={"email": f"{uuid.uuid4().hex}@example.com", "role": "admin"},
        headers=student_headers,
    )
    assert resp.status_code == 403
