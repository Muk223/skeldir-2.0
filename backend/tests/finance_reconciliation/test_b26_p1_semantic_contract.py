from __future__ import annotations

from decimal import Decimal

from app.finance_reconciliation.semantic_contract import (
    B26_P1_CONTRACT_VERSION,
    load_b26_p1_semantic_contract,
    semantic_contract_identity,
)
from app.revenue_verification.verification_coverage import (
    VerificationCoverageAggregate,
    compute_verification_coverage,
)


def test_b26_p1_contract_is_content_addressed_and_authority_only() -> None:
    contract = load_b26_p1_semantic_contract()
    identity = semantic_contract_identity()

    assert identity.contract_version == B26_P1_CONTRACT_VERSION
    assert len(identity.source_sha256) == 64
    assert len(identity.semantic_sha256) == 64
    assert contract["authority_kind"] == "semantic_constitution_not_financial_result"
    assert contract["projection_doctrine"]["trust_envelope"]["fields_created_in_P1"] is False


def test_b26_p1_golden_vector_uses_inherited_b23_metric() -> None:
    from datetime import datetime, timezone
    from uuid import UUID

    aggregate = VerificationCoverageAggregate(
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        currency_code="USD",
        window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        matched_webhook_revenue_minor=76000,
        connected_platform_revenue_minor=80000,
    )

    result = compute_verification_coverage(aggregate)

    assert result.coverage_percent == Decimal("95.00")
    assert result.denominator_connected_platform_revenue_minor == 80000


def test_b26_p1_provisional_coverage_is_not_confirmation() -> None:
    contract = load_b26_p1_semantic_contract()
    provisional = contract["truth_status"]["matched_provisional"]

    assert provisional["participates_in_coverage_numerator"] is True
    assert provisional["finance_truth_status"] == "provisional"
    assert provisional["may_be_relabelled_confirmed"] is False
