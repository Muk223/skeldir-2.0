"""
B0.6 Phase 0: Canonical v1 realtime revenue contract alignment tests.
"""

import os
from uuid import UUID

import pytest
from httpx import AsyncClient, ASGITransport

os.environ["TESTING"] = "1"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://app_user:Sk3ld1r_App_Pr0d_2025!@ep-lucky-base-aedv3gwo-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
)

from app.main import app  # noqa: E402

pytestmark = pytest.mark.asyncio


async def test_realtime_revenue_v1_response_shape():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/revenue/realtime",
            headers={
                "X-Correlation-ID": "00000000-0000-0000-0000-000000000000",
                "Authorization": "Bearer test-token",
            },
        )

    assert resp.status_code == 200
    body = resp.json()

    assert UUID(body["tenant_id"])
    assert isinstance(body["interval"], str)
    assert isinstance(body["currency"], str)
    assert isinstance(body["revenue_total"], (int, float))
    assert isinstance(body["verified"], bool)
    assert "data_as_of" in body
    if body["data_as_of"] is not None:
        assert isinstance(body["data_as_of"], str)
    assert "sources" in body
    assert isinstance(body["sources"], list)


async def test_realtime_revenue_v1_requires_authorization():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/revenue/realtime",
            headers={"X-Correlation-ID": "00000000-0000-0000-0000-000000000000"},
        )

    assert resp.status_code == 401
    body = resp.json()
    assert body["status"] == 401
    assert body["correlation_id"] == "00000000-0000-0000-0000-000000000000"
