"""
LLM workers routed through the provider choke point.

All provider execution, budget controls, breaker/timeout/cache, and llm_api_calls
persistence happen in app.llm.provider_boundary.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.provider_boundary import get_llm_provider_boundary
from app.models.llm import BudgetOptimizationJob, Investigation
from app.schemas.llm_payloads import LLMTaskPayload

logger = logging.getLogger(__name__)

_PROVIDER_BOUNDARY = get_llm_provider_boundary()


def _stable_fallback_id(model: LLMTaskPayload, endpoint: str, label: str) -> str:
    payload = {
        "tenant_id": str(model.tenant_id),
        "user_id": str(model.user_id),
        "endpoint": endpoint,
        "correlation_id": model.correlation_id,
        "request_id": model.request_id,
    }
    seed = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(f"{label}:{seed}".encode("utf-8")).hexdigest()
    return digest


def _resolve_request_id(model: LLMTaskPayload, endpoint: str) -> str:
    if model.request_id:
        return model.request_id
    if model.correlation_id:
        return model.correlation_id
    return _stable_fallback_id(model, endpoint, "request_id")


def _resolve_correlation_id(model: LLMTaskPayload, endpoint: str) -> str:
    if model.correlation_id:
        return model.correlation_id
    if model.request_id:
        return model.request_id
    return _stable_fallback_id(model, endpoint, "correlation_id")


def _normalize_payload_context(model: LLMTaskPayload, endpoint: str) -> LLMTaskPayload:
    return LLMTaskPayload.model_validate(
        {
            "tenant_id": model.tenant_id,
            "user_id": model.user_id,
            "correlation_id": _resolve_correlation_id(model, endpoint),
            "request_id": _resolve_request_id(model, endpoint),
            "prompt": model.prompt,
            "max_cost_cents": model.max_cost_cents,
        }
    )


async def route_request(
    model: LLMTaskPayload,
    session: AsyncSession,
    *,
    force_failure: bool = False,
) -> Dict[str, Any]:
    endpoint = "app.tasks.llm.route"
    payload = _normalize_payload_context(model, endpoint)
    result = await _PROVIDER_BOUNDARY.complete(
        model=payload,
        session=session,
        endpoint=endpoint,
        force_failure=force_failure,
    )
    logger.info(
        "llm_route_boundary",
        extra={
            "tenant_id": str(payload.tenant_id),
            "correlation_id": payload.correlation_id,
            "event_type": "llm.route",
            "request_id": payload.request_id,
            "status": result.status,
        },
    )
    return {
        "status": "accepted" if result.status == "success" else result.status,
        "route": "noop",
        "request_id": payload.request_id,
        "correlation_id": payload.correlation_id,
        "api_call_id": str(result.api_call_id),
        "blocked_reason": result.block_reason,
        "failure_reason": result.failure_reason,
        "was_cached": result.was_cached,
    }


async def generate_explanation(
    model: LLMTaskPayload,
    session: AsyncSession,
    *,
    force_failure: bool = False,
) -> Dict[str, Any]:
    endpoint = "app.tasks.llm.explanation"
    payload = _normalize_payload_context(model, endpoint)
    result = await _PROVIDER_BOUNDARY.complete(
        model=payload,
        session=session,
        endpoint=endpoint,
        force_failure=force_failure,
    )
    logger.info(
        "llm_explanation_boundary",
        extra={
            "tenant_id": str(payload.tenant_id),
            "correlation_id": payload.correlation_id,
            "event_type": "llm.explanation",
            "request_id": payload.request_id,
            "status": result.status,
        },
    )
    explanation = result.output_text if result.status == "success" else "not-available"
    return {
        "status": "accepted" if result.status == "success" else result.status,
        "explanation": explanation,
        "request_id": payload.request_id,
        "correlation_id": payload.correlation_id,
        "api_call_id": str(result.api_call_id),
        "blocked_reason": result.block_reason,
        "failure_reason": result.failure_reason,
        "was_cached": result.was_cached,
    }


async def run_investigation(
    model: LLMTaskPayload,
    session: AsyncSession,
    *,
    force_failure: bool = False,
) -> Dict[str, Any]:
    endpoint = "app.tasks.llm.investigation"
    payload = _normalize_payload_context(model, endpoint)
    result = await _PROVIDER_BOUNDARY.complete(
        model=payload,
        session=session,
        endpoint=endpoint,
        force_failure=force_failure,
    )
    query = f"provider:{payload.request_id}"
    existing = (
        await session.execute(
            select(Investigation.id).where(
                Investigation.tenant_id == payload.tenant_id,
                Investigation.query == query,
            )
        )
    ).scalar_one_or_none()
    investigation_id = existing
    if result.status == "success" and existing is None:
        investigation = Investigation(
            tenant_id=payload.tenant_id,
            query=query,
            status="completed",
            result={
                "status": "completed",
                "request_id": payload.request_id,
                "summary": result.output_text,
            },
            cost_cents=int(result.usage.get("cost_cents", 0)),
        )
        session.add(investigation)
        await session.flush()
        investigation_id = investigation.id

    logger.info(
        "llm_investigation_boundary",
        extra={
            "tenant_id": str(payload.tenant_id),
            "correlation_id": payload.correlation_id,
            "event_type": "llm.investigation",
            "request_id": payload.request_id,
            "status": result.status,
        },
    )
    return {
        "status": "accepted" if result.status == "success" else result.status,
        "investigation": "queued" if result.status == "success" else "blocked",
        "request_id": payload.request_id,
        "correlation_id": payload.correlation_id,
        "api_call_id": str(result.api_call_id),
        "investigation_id": str(investigation_id) if investigation_id else None,
        "blocked_reason": result.block_reason,
        "failure_reason": result.failure_reason,
        "was_cached": result.was_cached,
    }


async def optimize_budget(
    model: LLMTaskPayload,
    session: AsyncSession,
    *,
    force_failure: bool = False,
) -> Dict[str, Any]:
    endpoint = "app.tasks.llm.budget_optimization"
    payload = _normalize_payload_context(model, endpoint)
    result = await _PROVIDER_BOUNDARY.complete(
        model=payload,
        session=session,
        endpoint=endpoint,
        force_failure=force_failure,
    )
    existing = (
        await session.execute(
            select(BudgetOptimizationJob.id).where(
                BudgetOptimizationJob.tenant_id == payload.tenant_id,
                BudgetOptimizationJob.recommendations["request_id"].astext == payload.request_id,
            )
        )
    ).scalar_one_or_none()
    job_id = existing
    if result.status == "success" and existing is None:
        job = BudgetOptimizationJob(
            tenant_id=payload.tenant_id,
            status="completed",
            recommendations={
                "request_id": payload.request_id,
                "provider_summary": result.output_text,
                "status": "completed",
            },
            cost_cents=int(result.usage.get("cost_cents", 0)),
        )
        session.add(job)
        await session.flush()
        job_id = job.id

    logger.info(
        "llm_budget_boundary",
        extra={
            "tenant_id": str(payload.tenant_id),
            "correlation_id": payload.correlation_id,
            "event_type": "llm.budget_optimization",
            "request_id": payload.request_id,
            "status": result.status,
        },
    )
    return {
        "status": "accepted" if result.status == "success" else result.status,
        "budget_action": "noop" if result.status == "success" else "blocked",
        "request_id": payload.request_id,
        "correlation_id": payload.correlation_id,
        "api_call_id": str(result.api_call_id),
        "budget_job_id": str(job_id) if job_id else None,
        "blocked_reason": result.block_reason,
        "failure_reason": result.failure_reason,
        "was_cached": result.was_cached,
    }
