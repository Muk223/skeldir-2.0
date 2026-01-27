"""
Revenue API Routes (B0.6 Interim)

Canonical v1 surface for realtime revenue. Interim semantics: verified=false,
no platform fetch, no caching. Contract-first alignment only.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request, status

from app.api.problem_details import problem_details_response
from app.schemas.revenue import RealtimeRevenueV1Response

router = APIRouter()


@router.get(
    "/revenue/realtime",
    response_model=RealtimeRevenueV1Response,
    status_code=200,
    operation_id="getRealtimeRevenueV1",
    summary="Get realtime revenue (v1, interim)",
    description="Return interim realtime revenue payload aligned to B0.6 contract.",
)
async def get_realtime_revenue_v1(
    request: Request,
    x_correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
):
    """
    Canonical v1 realtime revenue endpoint.

    Contract: GET /api/v1/revenue/realtime
    Spec: api-contracts/dist/openapi/v1/revenue.bundled.yaml
    """
    if not _has_bearer_token(authorization):
        return problem_details_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Authentication Failed",
            detail="Missing or invalid Authorization header.",
            correlation_id=x_correlation_id,
            type_url="https://api.skeldir.com/problems/authentication-failed",
        )

    tenant_id = UUID(os.getenv("TEST_TENANT_ID", "00000000-0000-0000-0000-000000000000"))
    return {
        "tenant_id": tenant_id,
        "interval": "minute",
        "currency": "USD",
        "revenue_total": 125000.50,
        "verified": False,
        "data_as_of": datetime.now(timezone.utc),
        "sources": [],
    }


def _has_bearer_token(value: str | None) -> bool:
    if not value:
        return False
    stripped = value.strip()
    if not stripped.lower().startswith("bearer "):
        return False
    expected = os.getenv("B0_6_BEARER_TOKEN", "test-token")
    return stripped.split(" ", 1)[1] == expected
