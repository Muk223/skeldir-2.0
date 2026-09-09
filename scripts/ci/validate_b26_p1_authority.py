#!/usr/bin/env python3
"""Validate B2.6-P1 semantic, import-boundary, and CI authority."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

import yaml  # type: ignore[import-untyped]


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(REPO_ROOT))
CONTRACT_PATH = REPO_ROOT / "contracts/reconciliation/b2.6/semantic-authority.v1.yaml"
PROOF_REQUIREMENTS_PATH = (
    REPO_ROOT / "contracts/reconciliation/b2.6/proof-requirements.v1.yaml"
)
GOVERNANCE_PATH = REPO_ROOT / "contracts/reconciliation/b2.6/expected-governance.v1.yaml"
REQUIRED_STATUS_PATH = (
    REPO_ROOT
    / "contracts-internal/governance/b03_phase2_required_status_checks.main.json"
)
WORKFLOW_PATH = (
    REPO_ROOT / ".github/workflows/b2_6-p1-finance-reconciliation-adjudication.yml"
)
B26_PACKAGE = BACKEND / "app/finance_reconciliation"
PRODUCTION_DOCKERFILE = REPO_ROOT / "backend/Dockerfile"

GOVERNING_CONTEXT = "B2.6 Finance Reconciliation Adjudication"
DIAGNOSTIC_CONTEXT = "B2.6 P1 Exact-Main Diagnostics"
AGGREGATE_JOB = "b26-p1-finance-reconciliation-adjudication"
PRODUCER_JOBS = {
    "b26-p1-static-authority",
    "b26-p1-container-equivalence",
    "b26-p1-inherited-conduction",
}
EXPECTED_AGGREGATE_NAME = (
    "${{ github.event_name == 'push' && 'B2.6 P1 Exact-Main Diagnostics' "
    "|| 'B2.6 Finance Reconciliation Adjudication' }}"
)
EXPECTED_GATES = {
    "B26-P1-G1-G2-INHERITED-PHYSICS",
    "B26-P1-G3-G10-CONTAINER-EQUIVALENCE",
    "B26-P1-G4-SEMANTIC-AUTHORITY",
    "B26-P1-G8-EXECUTION-IDENTITY",
    "B26-P1-G9-NEGATIVE-CONTROLS",
}
EXPECTED_IDENTITY_FIELDS = {
    "gate_id",
    "phase",
    "contract_version",
    "contract_hash",
    "candidate_sha",
    "candidate_tree",
    "migration_head",
    "producer",
    "workflow",
    "event_type",
    "run_id",
    "artifact_hash",
    "scenario_id",
    "falsifier_id",
    "status",
}

FORBIDDEN_IMPORT_PREFIXES = (
    "app.services.revenue_reconciliation",
    "app.api.reconciliation",
    "app.api.export",
    "app.llm",
    "app.bayesian",
    "app.simulation",
    "app.explanation",
    "celery",
    "kombu",
)
FORBIDDEN_SQL_AUTHORITY_TOKENS = (
    "revenue_ledger",
    "reconciliation_runs",
    "attribution_allocations",
    "canonical_net_verified_amount_minor",
    "verified_amount_minor",
)


def _load_yaml(path: Path, *, base_loader: bool = False) -> Any:
    loader = yaml.BaseLoader if base_loader else yaml.SafeLoader
    return yaml.load(path.read_text(encoding="utf-8"), Loader=loader)


def _resolve_dotted(path: str) -> Any:
    module_name, _, attribute = path.rpartition(".")
    if not module_name or not attribute:
        raise ValueError(f"invalid_dotted_authority:{path}")
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def _imports(tree: ast.AST) -> Iterable[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def _migration_heads() -> set[str]:
    completed = subprocess.run(
        (sys.executable, "-m", "alembic", "heads"),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        match.group(1)
        for line in completed.stdout.splitlines()
        if (match := re.match(r"^([0-9a-f]+)\b", line.strip()))
    }


def _validate_contract_and_b23_binding(violations: list[str], details: dict[str, Any]) -> None:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://app_user:app_user@127.0.0.1:5432/b26_p1_static",
    )
    sys.path.insert(0, str(BACKEND))
    try:
        from app.finance_reconciliation.semantic_contract import (  # noqa: PLC0415
            load_b26_p1_semantic_contract,
            semantic_contract_identity,
        )
        from app.revenue_verification.verification_coverage import (  # noqa: PLC0415
            SUPPORTED_VERIFICATION_COVERAGE_CURRENCIES,
            SUPPORTED_VERIFICATION_COVERAGE_PLATFORMS,
            VerificationCoverageAggregate,
        )

        contract = load_b26_p1_semantic_contract()
        identity = semantic_contract_identity()
    except Exception as exc:  # noqa: BLE001
        violations.append(f"semantic_contract_refused:{exc}")
        return

    coverage = contract["coverage_authority"]
    migration_heads = _migration_heads()
    expected_migration_head = contract["migration_authority"]["expected_single_head"]
    if migration_heads != {expected_migration_head}:
        violations.append(
            "b26_p1_unjustified_migration_head_drift:"
            f"expected={expected_migration_head}:actual={sorted(migration_heads)}"
        )
    try:
        aggregate_callable = _resolve_dotted(coverage["aggregate_callable"])
        metric = _resolve_dotted(coverage["metric_object"])
        providers = _resolve_dotted(coverage["supported_provider_scope_reference"])
        currencies = _resolve_dotted(coverage["supported_currency_scope_reference"])
    except Exception as exc:  # noqa: BLE001
        violations.append(f"coverage_authority_unresolvable:{exc}")
        return

    if aggregate_callable.__module__ != "app.revenue_verification.verification_coverage":
        violations.append("coverage_aggregate_callable_not_b23_sovereign")
    if metric.__class__.__module__ != "app.revenue_verification.verification_coverage":
        violations.append("coverage_metric_object_not_b23_sovereign")
    if providers != SUPPORTED_VERIFICATION_COVERAGE_PLATFORMS:
        violations.append("coverage_provider_scope_reference_mismatch")
    if currencies != SUPPORTED_VERIFICATION_COVERAGE_CURRENCIES:
        violations.append("coverage_currency_scope_reference_mismatch")

    coverage_source = REPO_ROOT / "backend/app/revenue_verification/verification_coverage.py"
    source_ast_hash = hashlib.sha256(
        ast.dump(
            ast.parse(coverage_source.read_text(encoding="utf-8")),
            include_attributes=False,
        ).encode("utf-8")
    ).hexdigest()
    if source_ast_hash != coverage.get("implementation_ast_sha256"):
        violations.append(
            "coverage_implementation_identity_mismatch:"
            f"expected={coverage.get('implementation_ast_sha256')}:actual={source_ast_hash}"
        )

    vector = coverage["golden_falsification_vector"]
    aggregate = VerificationCoverageAggregate(
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        currency_code="USD",
        window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        matched_webhook_revenue_minor=vector["matched_minor"],
        connected_platform_revenue_minor=vector["connected_supported_minor"],
    )
    observed = metric.compute(aggregate).coverage_percent
    if observed != Decimal(vector["required_percent"]):
        violations.append(f"coverage_golden_vector_wrong:{observed}")
    if observed == Decimal(vector["forbidden_percent"]):
        violations.append("coverage_total_business_denominator_reentered")

    details.update(
        {
            "contract_source_sha256": identity.source_sha256,
            "contract_semantic_sha256": identity.semantic_sha256,
            "coverage_implementation_ast_sha256": source_ast_hash,
            "coverage_observed_percent": str(observed),
            "coverage_providers": sorted(providers),
            "coverage_currencies": sorted(currencies),
            "migration_heads": sorted(migration_heads),
        }
    )


def _validate_b26_namespace(violations: list[str], details: dict[str, Any]) -> None:
    files = sorted(B26_PACKAGE.rglob("*.py"))
    if {path.name for path in files} != {"__init__.py", "semantic_contract.py"}:
        violations.append("b26_p1_product_machinery_or_unregistered_module_present")
    for path in files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for imported in _imports(tree):
            if any(
                imported == prefix or imported.startswith(prefix + ".")
                for prefix in FORBIDDEN_IMPORT_PREFIXES
            ):
                violations.append(
                    f"b26_false_authority_import:{path.relative_to(REPO_ROOT)}:{imported}"
                )
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, float):
                violations.append(
                    f"b26_authoritative_float_literal:{path.relative_to(REPO_ROOT)}:{node.lineno}"
                )
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                lowered = node.value.lower()
                if "select " in lowered or "sum(" in lowered:
                    if any(token in lowered for token in FORBIDDEN_SQL_AUTHORITY_TOKENS):
                        violations.append(
                            f"b26_duplicate_financial_sql:{path.relative_to(REPO_ROOT)}:{node.lineno}"
                        )
    details["b26_namespace_files"] = [
        path.relative_to(REPO_ROOT).as_posix() for path in files
    ]


def _validate_governance(violations: list[str], details: dict[str, Any]) -> None:
    for path in (
        PROOF_REQUIREMENTS_PATH,
        GOVERNANCE_PATH,
        REQUIRED_STATUS_PATH,
        WORKFLOW_PATH,
    ):
        if not path.is_file():
            violations.append(f"required_authority_file_missing:{path.relative_to(REPO_ROOT)}")
    if violations:
        return
    governance = _load_yaml(GOVERNANCE_PATH)
    requirements = _load_yaml(PROOF_REQUIREMENTS_PATH)
    required_status = json.loads(REQUIRED_STATUS_PATH.read_text(encoding="utf-8"))
    workflow = _load_yaml(WORKFLOW_PATH, base_loader=True)
    triggers = workflow.get("on", {})
    if set(triggers) != {"pull_request", "merge_group", "push"}:
        violations.append(f"b26_workflow_event_identity_drift:{sorted(triggers)}")
    push = triggers.get("push", {})
    if push.get("branches") != ["main"]:
        violations.append("b26_push_diagnostic_not_exact_main")
    jobs = workflow.get("jobs", {})
    if set(PRODUCER_JOBS) - set(jobs):
        violations.append("b26_required_producer_job_missing")
    aggregate = jobs.get(AGGREGATE_JOB, {})
    if aggregate.get("name") != EXPECTED_AGGREGATE_NAME:
        violations.append("b26_required_context_event_identity_ambiguous")
    if aggregate.get("if") != "always()":
        violations.append("b26_aggregate_not_fail_closed_always")
    if set(aggregate.get("needs", [])) != PRODUCER_JOBS:
        violations.append("b26_aggregate_dependency_set_drift")
    names = [str(job.get("name", "")) for job in jobs.values()]
    if sum(GOVERNING_CONTEXT in name for name in names) != 1:
        violations.append("b26_governing_context_emitter_count_not_one")
    if governance.get("required_context") != GOVERNING_CONTEXT:
        violations.append("b26_expected_governance_context_drift")
    if governance.get("diagnostic_context") != DIAGNOSTIC_CONTEXT:
        violations.append("b26_expected_diagnostic_context_drift")
    if set(governance.get("required_producer_jobs", [])) != PRODUCER_JOBS:
        violations.append("b26_expected_governance_producers_drift")
    if set(governance.get("governing_events", [])) != {"pull_request", "merge_group"}:
        violations.append("b26_governing_event_set_drift")
    if set(governance.get("required_context_must_not_emit_on", [])) != {
        "push",
        "workflow_dispatch",
    }:
        violations.append("b26_required_context_exclusion_set_drift")
    proof_cells = requirements.get("required_cells", [])
    if {cell.get("gate_id") for cell in proof_cells} != EXPECTED_GATES:
        violations.append("b26_proof_gate_census_drift")
    if {cell.get("producer") for cell in proof_cells} != {
        "b26-p1-static-authority",
        "b26-p1-container-equivalence",
        "b26-p1-inherited-conduction",
    }:
        violations.append("b26_proof_producer_census_drift")
    if set(requirements.get("required_identity_fields", [])) != EXPECTED_IDENTITY_FIELDS:
        violations.append("b26_proof_identity_fields_drift")
    if set(requirements.get("accepted_events", [])) != {
        "pull_request",
        "merge_group",
        "push",
    }:
        violations.append("b26_proof_accepted_events_drift")
    required_contexts = required_status.get("required_contexts", [])
    if required_contexts.count(GOVERNING_CONTEXT) != 1:
        violations.append("b26_required_status_contract_binding_missing")
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    required_tokens = (
        "validate_b26_p1_authority.py",
        "test_b26_p1_negative_controls.py",
        "assert_b26_p1_container_equivalence.py",
        "attest_b26_p1_inherited_conduction.py",
        "adjudicate_b26_p1_proof_plane.py",
        "if-no-files-found: error",
    )
    for token in required_tokens:
        if token not in workflow_text:
            violations.append(f"b26_workflow_required_wiring_missing:{token}")
    details["workflow_events"] = sorted(triggers)
    details["aggregate_producers"] = sorted(PRODUCER_JOBS)


def validate() -> tuple[list[str], dict[str, Any]]:
    violations: list[str] = []
    details: dict[str, Any] = {}
    _validate_contract_and_b23_binding(violations, details)
    _validate_b26_namespace(violations, details)
    _validate_governance(violations, details)
    dockerfile = PRODUCTION_DOCKERFILE.read_text(encoding="utf-8")
    if "COPY contracts/reconciliation /app/contracts/reconciliation" not in dockerfile:
        violations.append("b26_contract_not_shipped_in_production_image")
    return violations, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    violations, details = validate()
    if violations:
        print("B26_P1_AUTHORITY_FAIL")
        for violation in violations:
            print(violation)
        return 1
    if args.evidence_dir:
        from scripts.ci.b26_p1_evidence import write_evidence_cell  # noqa: PLC0415

        write_evidence_cell(
            args.evidence_dir / "semantic-authority.json",
            gate_id="B26-P1-G4-SEMANTIC-AUTHORITY",
            producer="b26-p1-static-authority",
            scenario_id="semantic-authority-pristine",
            falsifier_id="B26-P1-NC-01-through-04",
            details=details,
        )
        write_evidence_cell(
            args.evidence_dir / "execution-identity.json",
            gate_id="B26-P1-G8-EXECUTION-IDENTITY",
            producer="b26-p1-static-authority",
            scenario_id="governing-workflow-pristine",
            falsifier_id="B26-P1-NC-05",
            details={
                "workflow_events": details["workflow_events"],
                "aggregate_producers": details["aggregate_producers"],
                "governing_context": GOVERNING_CONTEXT,
                "diagnostic_context": DIAGNOSTIC_CONTEXT,
            },
        )
    print("B26_P1_AUTHORITY_PASS")
    print(json.dumps(details, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
