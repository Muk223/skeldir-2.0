from __future__ import annotations

from decimal import Decimal

from app.finance_reconciliation.semantic_contract import (
    B26_DISCREPANCY_TAXONOMY_V1,
    B26_P1_CONTRACT_VERSION,
    B26_P1_SUPERSEDES_VERSION,
    B26_REQUIRED_DISCREPANCY_REASONS,
    B26_SUCCESSOR_STATUS_NONE,
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


def test_b26_p1_discrepancy_taxonomy_is_machine_governed() -> None:
    contract = load_b26_p1_semantic_contract()
    discrepancy = contract["finance_discrepancy_reasons"]

    assert discrepancy["taxonomy_version"] == B26_DISCREPANCY_TAXONOMY_V1
    assert set(discrepancy["required_reasons"]) == set(B26_REQUIRED_DISCREPANCY_REASONS)
    assert len(discrepancy["required_reasons"]) == 8
    # Governed additive slot is empty at P1 closure; baseline alone is law.
    assert discrepancy["additional_governed_reasons"] == []
    # Collapsed category must stay empty so no consumer mistakes it for authority.
    assert contract["required_reconciliation_reasons"] == []
    # Separated ontologies preserve the superseded nine meanings without collapse.
    assert set(contract["truth_state_vocabulary"]) == {
        "matched_confirmed",
        "matched_provisional",
        "adjusted_confirmed",
    }
    assert set(contract["scope_dispositions"]) == {
        "supported_unresolved",
        "unsupported_provider_excluded",
        "unsupported_currency_excluded",
        "outside_governed_window_excluded",
        "source_identity_unresolved",
        "authority_unavailable",
    }


def test_b26_p1_tenant_and_seam_are_sensed() -> None:
    contract = load_b26_p1_semantic_contract()
    tenant = contract["tenant_identifier_policy"]

    assert tenant["durable_state"] == "tenant_scoped"
    assert tenant["external_raw_tenant_id"] == "forbidden"
    assert set(contract["future_insertion_seam"]) == {
        "B2.3_deterministic_verdict_and_coverage_authority",
        "future_B2.6_deterministic_reconciliation_projection_boundary",
        "future_finance_projection",
        "future_B2.6_TrustEnvelope_projection",
    }


def test_b26_p1_authority_classes_distinguish_permanent_from_closure() -> None:
    contract = load_b26_p1_semantic_contract()
    classes = contract["authority_classes"]

    assert classes["finance_discrepancy_reasons"] == "PERMANENT_MACHINE_ENFORCED"
    assert classes["tenant_identifier_policy"] == "PERMANENT_MACHINE_ENFORCED"
    assert classes["future_insertion_seam"] == "PERMANENT_MACHINE_ENFORCED"
    assert classes["migration_authority.expected_single_head"] == "PHASE_LOCAL_CLOSURE_FACT"
    assert classes["closure_snapshot"] == "PHASE_LOCAL_CLOSURE_FACT"
    assert classes["coverage_authority.denominator.definition"] == "DOCUMENTATION_ONLY"
    assert classes["successor_product_authorization"] == "PERMANENT_MACHINE_ENFORCED"
    assert classes["supersession"] == "DOCUMENTATION_ONLY"
    snapshot = contract["closure_snapshot"]
    assert snapshot["p1_closure_migration_head"] == "202609072001"


def test_b26_p1_version_identity_is_unambiguous() -> None:
    contract = load_b26_p1_semantic_contract()

    assert B26_P1_CONTRACT_VERSION == "b2.6-p1-semantic-authority-v2"
    assert contract["contract_version"] == B26_P1_CONTRACT_VERSION
    supersession = contract["supersession"]
    assert supersession["supersedes"] == B26_P1_SUPERSEDES_VERSION
    assert supersession["supersedes"] != B26_P1_CONTRACT_VERSION
    assert isinstance(supersession["reason"], str) and supersession["reason"]
    assert contract["closure_snapshot"]["p1_closure_contract_version"] == (
        B26_P1_CONTRACT_VERSION
    )


def test_b26_p1_successor_product_gate_defaults_to_closure() -> None:
    contract = load_b26_p1_semantic_contract()
    successor = contract["successor_product_authorization"]

    assert successor["status"] == B26_SUCCESSOR_STATUS_NONE
    assert successor["authorized_machinery"] == []
