from __future__ import annotations

from app.llm.provider_boundary import get_llm_provider_boundary


def test_provider_boundary_stub_is_callable_and_deterministic():
    boundary = get_llm_provider_boundary()
    result = boundary.complete(prompt={"task": "noop"}, max_cost_cents=0)
    assert boundary.boundary_id == "b07_p0_stub"
    assert result.provider == "stub"
    assert result.model == "stub"
    assert result.output_text == "stubbed"
    assert result.usage["cost_cents"] == 0

