from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.identity import SYSTEM_USER_ID
from app.db.session import get_session
from app.llm.provider_boundary import get_llm_provider_boundary
from app.schemas.llm_payloads import LLMTaskPayload


@pytest.mark.asyncio
async def test_provider_boundary_stub_is_callable_and_deterministic(test_tenant):
    boundary = get_llm_provider_boundary()
    model = LLMTaskPayload(
        tenant_id=test_tenant,
        user_id=SYSTEM_USER_ID,
        correlation_id=str(uuid4()),
        request_id=str(uuid4()),
        prompt={"task": "noop", "cache_enabled": False},
        max_cost_cents=5,
    )
    async with get_session(tenant_id=test_tenant, user_id=SYSTEM_USER_ID) as session:
        result = await boundary.complete(
            model=model,
            session=session,
            endpoint="app.tasks.llm.explanation",
        )
    assert boundary.boundary_id == "b07_p3_aisuite_chokepoint"
    assert result.provider == "stub"
    assert result.status == "success"
    assert result.output_text
    assert result.usage["cost_cents"] >= 0
