from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.identity import SYSTEM_USER_ID
from app.db.session import get_session
from app.models.llm import LLMBudgetReservation, LLMApiCall
from app.schemas.llm_payloads import LLMTaskPayload
from app.workers.llm import _resolve_request_id, generate_explanation, route_request


def _payload(tenant_id: UUID, *, request_id: str | None = None) -> LLMTaskPayload:
    return LLMTaskPayload(
        tenant_id=tenant_id,
        user_id=SYSTEM_USER_ID,
        correlation_id=str(uuid4()),
        request_id=request_id,
        prompt={"simulated_output_text": "worker-test"},
        max_cost_cents=10,
    )


def test_llm_fallback_id_ignores_prompt_variation() -> None:
    tenant_id = uuid4()
    payload_a = LLMTaskPayload(
        tenant_id=tenant_id,
        user_id=SYSTEM_USER_ID,
        correlation_id=None,
        request_id=None,
        prompt={"question": "why deterministic?"},
        max_cost_cents=10,
    )
    payload_b = LLMTaskPayload(
        tenant_id=tenant_id,
        user_id=SYSTEM_USER_ID,
        correlation_id=None,
        request_id=None,
        prompt={"question": "why  deterministic?", "whitespace": True},
        max_cost_cents=10,
    )
    assert _resolve_request_id(payload_a, "app.tasks.llm.route") == _resolve_request_id(
        payload_b, "app.tasks.llm.route"
    )


@pytest.mark.asyncio
async def test_llm_route_writes_single_audit_row(test_tenant) -> None:
    payload = _payload(test_tenant, request_id=str(uuid4()))
    async with get_session(tenant_id=test_tenant, user_id=SYSTEM_USER_ID) as session:
        result = await route_request(payload, session=session)

    async with get_session(tenant_id=test_tenant, user_id=SYSTEM_USER_ID) as session:
        row = await session.get(LLMApiCall, UUID(result["api_call_id"]))
        assert row is not None
        assert row.status == "success"
        assert row.provider in {"stub", "pending", "blocked", "error", "timeout"}
        assert row.distillation_eligible is False


@pytest.mark.asyncio
async def test_llm_explanation_retry_idempotent_no_double_debit(test_tenant) -> None:
    request_id = str(uuid4())
    payload = _payload(test_tenant, request_id=request_id)
    payload.prompt = {
        "simulated_output_text": "retry-idempotent",
        "simulated_cost_cents": 4,
    }

    async with get_session(tenant_id=test_tenant, user_id=SYSTEM_USER_ID) as session:
        first = await generate_explanation(payload, session=session)
        second = await generate_explanation(payload, session=session)

    assert first["api_call_id"] == second["api_call_id"]

    async with get_session(tenant_id=test_tenant, user_id=SYSTEM_USER_ID) as session:
        api_rows = (
            await session.execute(
                select(LLMApiCall).where(
                    LLMApiCall.tenant_id == test_tenant,
                    LLMApiCall.user_id == SYSTEM_USER_ID,
                    LLMApiCall.request_id == request_id,
                    LLMApiCall.endpoint == "app.tasks.llm.explanation",
                )
            )
        ).scalars().all()
        res_rows = (
            await session.execute(
                select(LLMBudgetReservation).where(
                    LLMBudgetReservation.tenant_id == test_tenant,
                    LLMBudgetReservation.user_id == SYSTEM_USER_ID,
                    LLMBudgetReservation.request_id == request_id,
                    LLMBudgetReservation.endpoint == "app.tasks.llm.explanation",
                )
            )
        ).scalars().all()
        assert len(api_rows) == 1
        assert len(res_rows) == 1
