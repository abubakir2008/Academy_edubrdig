"""Catalog department: Postgres full-text search replaces ElasticSearch.

Regression coverage for the migration off ElasticSearch — /search/tutors now
queries the Tutors module's own table (search_vector, a generated tsvector
column) in the same process, rather than a separately-indexed ES document.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import mint_access_token

pytestmark = pytest.mark.asyncio


async def _make_tutor(client, token, headline, description, price_cents=1000):
    resp = await client.post(
        "/tutors/me",
        json={"headline": headline, "description": description, "price_cents": price_cents},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.parametrize("department_app", ["catalog"], indirect=True)
async def test_search_finds_tutor_by_headline_text(department_app):
    _main, client = department_app

    tutor_a = mint_access_token(str(uuid.uuid4()), "tutor")
    tutor_b = mint_access_token(str(uuid.uuid4()), "tutor")
    await _make_tutor(client, tutor_a, "Conversational Spanish coach", "Fun, relaxed lessons.")
    await _make_tutor(client, tutor_b, "Advanced calculus tutor", "Exam prep specialist.")

    resp = await client.get("/search/tutors", params={"q": "spanish"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["results"][0]["headline"] == "Conversational Spanish coach"


@pytest.mark.parametrize("department_app", ["catalog"], indirect=True)
async def test_search_respects_price_filter(department_app):
    _main, client = department_app

    cheap = mint_access_token(str(uuid.uuid4()), "tutor")
    pricey = mint_access_token(str(uuid.uuid4()), "tutor")
    await _make_tutor(client, cheap, "Budget French tutor", "Affordable lessons.", price_cents=500)
    await _make_tutor(client, pricey, "Premium French tutor", "Native, certified.", price_cents=9000)

    resp = await client.get("/search/tutors", params={"q": "french", "max_price_cents": 1000})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["results"][0]["headline"] == "Budget French tutor"
