"""
Attribution API Routes

Implements attribution operations defined in api-contracts/dist/openapi/v1/attribution.bundled.yaml

Contract Operations:
- GET /api/attribution/revenue/realtime: Get realtime revenue attribution data

All routes use generated Pydantic models from backend/app/schemas/attribution.py
"""

from fastapi import APIRouter, Header, Request, Response, status
from uuid import UUID
from typing import Annotated

# Import generated Pydantic models
from app.schemas.attribution import RealtimeRevenueResponse
from app.api.problem_details import problem_details_response

router = APIRouter()


@router.get(
    "/revenue/realtime",
    response_model=RealtimeRevenueResponse,
    status_code=200,
    operation_id="getRealtimeRevenue",
    summary="Get realtime revenue attribution data",
    description="Retrieve realtime revenue attribution data with verification status and data freshness"
)
async def get_realtime_revenue(
    request: Request,
    response: Response,
    x_correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
):
    """
    Get realtime revenue attribution data.
    
    Phase F: Interim Semantics Implementation
    Returns unverified revenue data with upgrade notice during B0.1 phase.
    
    Contract: GET /api/attribution/revenue/realtime
    Spec: api-contracts/dist/openapi/v1/attribution.bundled.yaml
    
    Returns:
        RealtimeRevenueResponse: Revenue data with verification status
    """
    # Phase B0.1: Return unverified data with upgrade notice
    # Semantic alignment: verified=false reflects actual system capabilities
    # upgrade_notice guides users about data limitations
    
    import os
    from datetime import datetime

    # Minimal auth guard to align with contract (no JWT verification in B0.1).
    if not _has_bearer_token(authorization):
        return problem_details_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Authentication Failed",
            detail="Missing or invalid Authorization header.",
            correlation_id=x_correlation_id,
            type_url="https://api.skeldir.com/problems/authentication-failed",
        )

    # System phase determines verification status
    system_phase = os.getenv('SYSTEM_PHASE', 'B0.1')
    tenant_id = os.getenv('TEST_TENANT_ID', '00000000-0000-0000-0000-000000000000')

    # In B0.1: Revenue data is NOT verified (no reconciliation pipeline yet)
    verified = False if system_phase == 'B0.1' else True

    # Construct response with proper semantics
    response_data = {
        "total_revenue": 125000.50,
        "event_count": 0,  # Stub value for B0.1 (no event tracking yet)
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "data_freshness_seconds": 45,
        "verified": verified,
        "tenant_id": tenant_id,
    }

    # Add upgrade_notice when data is unverified (interim state)
    if not verified:
        response_data["upgrade_notice"] = (
            "Revenue data pending reconciliation. "
            "Full statistical verification available in Phase B2.6."
        )

    etag = _compute_etag(response_data)
    if if_none_match and if_none_match.strip() == etag:
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={
                "ETag": etag,
                "Cache-Control": "max-age=30",
            },
        )

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "max-age=30"
    return response_data


def _has_bearer_token(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower().startswith("bearer ")


def _compute_etag(payload: dict) -> str:
    import hashlib
    import json

    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"\"{digest}\""

