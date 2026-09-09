"""Runtime-resolvable B2.6-P1 semantic constitution.

This module loads and validates authority metadata only. It intentionally owns
no reconciliation calculation or financial state. Future B2.6 consumers must
cite this contract and the B2.3 callable it names; CI rejects a second coverage
implementation or a dependency on a fenced legacy surface.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml  # type: ignore[import-untyped]


_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = (
    _PACKAGE_ROOT.parent
    if (_PACKAGE_ROOT.parent / "contracts/reconciliation").is_dir()
    else _PACKAGE_ROOT
)
B26_P1_SEMANTIC_CONTRACT_PATH = (
    _REPO_ROOT / "contracts/reconciliation/b2.6/semantic-authority.v1.yaml"
)
B26_P1_CONTRACT_VERSION = "b2.6-p1-semantic-authority-v1"

_REQUIRED_TOP_LEVEL = frozenset(
    {
        "phase_id",
        "contract_version",
        "maturity_mode",
        "authority_kind",
        "migration_authority",
        "coverage_authority",
        "truth_status",
        "required_reconciliation_reasons",
        "money_authority",
        "projection_doctrine",
        "tenant_identifier_policy",
        "ontological_authority",
        "authority_map",
        "legacy_false_authorities",
        "future_insertion_seam",
        "negative_control_registry",
        "proof_artifact_identity_requirements",
        "prohibited_P1_product_machinery",
    }
)


class SemanticContractError(ValueError):
    """Raised when B2.6 semantic authority is absent, malformed, or weakened."""


@dataclass(frozen=True)
class SemanticContractIdentity:
    """Exact source and semantic identities of the governing contract."""

    phase: str
    contract_version: str
    source_sha256: str
    semantic_sha256: str


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise SemanticContractError(reason)


def _validate_contract(document: Mapping[str, Any]) -> None:
    missing = sorted(_REQUIRED_TOP_LEVEL - set(document))
    _require(not missing, f"b26_p1_contract_missing_fields:{','.join(missing)}")
    _require(document["phase_id"] == "B2.6-P1", "b26_p1_phase_mismatch")
    _require(
        document["contract_version"] == B26_P1_CONTRACT_VERSION,
        "b26_p1_contract_version_mismatch",
    )
    _require(
        document["maturity_mode"] == "DESIGN_PARTNER_MODE",
        "b26_p1_maturity_mode_mismatch",
    )
    migration = document["migration_authority"]
    _require(
        migration.get("schema_change_required_in_P1") is False
        and migration.get("expected_single_head") == "202609072001",
        "b26_p1_migration_authority_drift",
    )

    coverage = document["coverage_authority"]
    _require(isinstance(coverage, dict), "b26_p1_coverage_authority_not_object")
    _require(
        coverage.get("aggregate_callable")
        == "app.revenue_verification.verification_coverage."
        "fetch_verification_coverage_aggregate",
        "b26_p1_coverage_aggregate_authority_drift",
    )
    _require(
        coverage.get("metric_object")
        == "app.revenue_verification.verification_coverage.VERIFICATION_COVERAGE",
        "b26_p1_coverage_metric_authority_drift",
    )
    implementation_hash = coverage.get("implementation_ast_sha256")
    _require(
        isinstance(implementation_hash, str)
        and len(implementation_hash) == 64
        and all(character in "0123456789abcdef" for character in implementation_hash),
        "b26_p1_coverage_implementation_hash_invalid",
    )
    vector = coverage.get("golden_falsification_vector", {})
    _require(
        vector
        == {
            "matched_minor": 76000,
            "connected_supported_minor": 80000,
            "total_business_minor": 100000,
            "required_percent": "95.00",
            "forbidden_percent": "76.00",
        },
        "b26_p1_coverage_golden_vector_drift",
    )
    unsupported = coverage.get("unsupported_rail_doctrine", {})
    _require(
        unsupported.get("numerator") == "excluded"
        and unsupported.get("denominator") == "excluded",
        "b26_p1_unsupported_rail_denominator_drift",
    )

    truth_status = document["truth_status"]
    provisional = truth_status.get("matched_provisional", {})
    _require(
        truth_status.get("coverage_is_not_final_finance_confirmation") is True,
        "b26_p1_coverage_confirmation_conflation",
    )
    _require(
        provisional.get("participates_in_coverage_numerator") is True
        and provisional.get("finance_truth_status") == "provisional"
        and provisional.get("may_be_relabelled_confirmed") is False,
        "b26_p1_provisional_semantics_drift",
    )

    money = document["money_authority"]
    _require(
        money.get("representation") == "integer_minor_units"
        and money.get("authoritative_float_or_decimal_major_units") == "forbidden",
        "b26_p1_integer_money_authority_drift",
    )
    projections = document["projection_doctrine"]
    for projection_name in ("finance_export", "trust_envelope"):
        projection = projections.get(projection_name, {})
        _require(
            projection.get("authority") == "projection_only"
            and projection.get("recomputation") == "forbidden",
            f"b26_p1_projection_authority_drift:{projection_name}",
        )

    ontology = document["ontological_authority"]
    for key in (
        "B2.4_estimation_financial_authority",
        "B2.13_counterfactual_financial_authority",
        "LLM_financial_or_classification_authority",
    ):
        _require(ontology.get(key) == "NONE", f"b26_p1_false_authority:{key}")

    false_ids = {
        str(entry.get("id"))
        for entry in document["legacy_false_authorities"]
        if isinstance(entry, dict)
    }
    _require(
        false_ids
        == {
            "legacy_reconciliation_service",
            "legacy_revenue_ledger",
            "legacy_reconciliation_api",
            "route_local_source_alias_arithmetic",
            "allocation_grain_export_recomputation",
        },
        "b26_p1_false_authority_registry_drift",
    )
    _require(
        len(document["required_reconciliation_reasons"]) == 9,
        "b26_p1_reason_set_incomplete",
    )
    _require(
        len(document["negative_control_registry"]) >= 7,
        "b26_p1_negative_control_registry_incomplete",
    )
    _require(
        "reconciliation_business_table" in document["prohibited_P1_product_machinery"],
        "b26_p1_product_scope_fence_missing",
    )


@lru_cache(maxsize=1)
def load_b26_p1_semantic_contract() -> Mapping[str, Any]:
    """Load the exact shipped contract and fail closed on any semantic drift."""
    if not B26_P1_SEMANTIC_CONTRACT_PATH.is_file():
        raise SemanticContractError(
            f"b26_p1_contract_missing:{B26_P1_SEMANTIC_CONTRACT_PATH.as_posix()}"
        )
    document = yaml.safe_load(
        B26_P1_SEMANTIC_CONTRACT_PATH.read_text(encoding="utf-8")
    )
    if not isinstance(document, dict):
        raise SemanticContractError("b26_p1_contract_not_object")
    _validate_contract(document)
    return document


def semantic_contract_identity() -> SemanticContractIdentity:
    """Return byte and semantic hashes recoverable inside a shipped image."""
    document = load_b26_p1_semantic_contract()
    source = B26_P1_SEMANTIC_CONTRACT_PATH.read_bytes()
    return SemanticContractIdentity(
        phase="B2.6-P1",
        contract_version=B26_P1_CONTRACT_VERSION,
        source_sha256=hashlib.sha256(source).hexdigest(),
        semantic_sha256=hashlib.sha256(_canonical_json(document)).hexdigest(),
    )


if __name__ == "__main__":
    print(json.dumps(semantic_contract_identity().__dict__, sort_keys=True))
