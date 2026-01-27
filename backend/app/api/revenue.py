"""
Revenue API Routes (B0.6 Interim)

Canonical v1 surface for realtime revenue. Interim semantics: verified=false,
no platform fetch, no caching. Contract-first alignment only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db_session
from app.schemas.revenue import RealtimeRevenueV1Response
from app.security.auth import AuthContext, get_auth_context

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
    x_correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")],
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Canonical v1 realtime revenue endpoint.

    Contract: GET /api/v1/revenue/realtime
    Spec: api-contracts/dist/openapi/v1/revenue.bundled.yaml
    """
    _ = db_session
    tenant_id = auth_context.tenant_id
    return {
        "tenant_id": tenant_id,
        "interval": "minute",
        "currency": "USD",
        "revenue_total": 125000.50,
        "verified": False,
        "data_as_of": datetime.now(timezone.utc),
        "sources": [],
    }
