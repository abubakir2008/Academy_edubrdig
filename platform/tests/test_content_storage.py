"""Content department: storage ownership boundary.

Objects are namespaced `{user_id}/{uuid}-{filename}` (see storage.py's
presign_upload/upload_file). `presign-download` used to hand back a signed
URL for *any* object_name a caller supplied, with only `get_current_user` —
no check that the caller actually owns that object. These tests only cover
the 403/staff-bypass boundary itself, which is checked before any MinIO
call, so they don't need a live MinIO to pass.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import mint_access_token

pytestmark = pytest.mark.asyncio


def _headers(role: str, user_id: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_access_token(user_id or str(uuid.uuid4()), role)}"}


@pytest.mark.parametrize("department_app", ["content"], indirect=True)
async def test_cannot_presign_download_for_someone_elses_object(department_app):
    _main, client = department_app
    other_users_object = f"{uuid.uuid4()}/{uuid.uuid4().hex}-secret.pdf"

    resp = await client.post(
        "/storage/presign-download",
        json={"bucket": "documents", "object_name": other_users_object},
        headers=_headers("student"),
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize("department_app", ["content"], indirect=True)
async def test_owner_is_allowed_past_the_ownership_check(department_app):
    """The route still reaches the (unconfigured-in-tests) MinIO call for the
    owner's own object — 503 here means the ownership gate let it through,
    not that ownership was denied."""
    _main, client = department_app
    owner_id = str(uuid.uuid4())
    own_object = f"{owner_id}/{uuid.uuid4().hex}-notes.pdf"

    resp = await client.post(
        "/storage/presign-download",
        json={"bucket": "documents", "object_name": own_object},
        headers=_headers("student", user_id=owner_id),
    )
    assert resp.status_code != 403, resp.text


@pytest.mark.parametrize("department_app", ["content"], indirect=True)
async def test_staff_can_presign_download_any_object(department_app):
    _main, client = department_app
    other_users_object = f"{uuid.uuid4()}/{uuid.uuid4().hex}-secret.pdf"

    resp = await client.post(
        "/storage/presign-download",
        json={"bucket": "documents", "object_name": other_users_object},
        headers=_headers("admin"),
    )
    assert resp.status_code != 403, resp.text
