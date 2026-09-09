#!/usr/bin/env python3
"""Apply one reviewable B2.6-P1 on-disk controlled defect."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts/reconciliation/b2.6/semantic-authority.v1.yaml"
SEMANTIC_MODULE = ROOT / "backend/app/finance_reconciliation/semantic_contract.py"
WORKFLOW = ROOT / ".github/workflows/b2_6-p1-finance-reconciliation-adjudication.yml"
DOCKERFILE = ROOT / "backend/Dockerfile"


def _replace_once(path: Path, old: str, new: str, *, defect: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{defect}:anchor_count={text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def mandatory_semantic_element() -> None:
    _replace_once(CONTRACT, "maturity_mode: DESIGN_PARTNER_MODE\n", "", defect="mandatory_semantic_element")


def coverage_authority_reference() -> None:
    _replace_once(
        CONTRACT,
        "  aggregate_callable: app.revenue_verification.verification_coverage.fetch_verification_coverage_aggregate\n",
        "  aggregate_callable: app.services.revenue_reconciliation.RevenueReconciliationService\n",
        defect="coverage_authority_reference",
    )


def legacy_false_authority_import() -> None:
    _replace_once(
        SEMANTIC_MODULE,
        "import yaml  # type: ignore[import-untyped]\n",
        "import yaml  # type: ignore[import-untyped]\n"
        "from app.services.revenue_reconciliation import RevenueReconciliationService  # NC-B26-P1-03\n",
        defect="legacy_false_authority_import",
    )


def ontological_authority() -> None:
    _replace_once(
        CONTRACT,
        "  LLM_financial_or_classification_authority: NONE\n",
        "  LLM_financial_or_classification_authority: DERIVED\n",
        defect="ontological_authority",
    )


def workflow_execution_identity() -> None:
    _replace_once(
        WORKFLOW,
        "    name: ${{ github.event_name == 'push' && 'B2.6 P1 Exact-Main Diagnostics' || 'B2.6 Finance Reconciliation Adjudication' }}\n",
        "    name: B2.6 Finance Reconciliation Adjudication\n",
        defect="workflow_execution_identity",
    )


def container_contract_copy() -> None:
    _replace_once(
        DOCKERFILE,
        "COPY contracts/reconciliation /app/contracts/reconciliation\n",
        "COPY contracts/reconciliation/v1 /app/contracts/reconciliation/v1\n",
        defect="container_contract_copy",
    )


DEFECTS: dict[str, Callable[[], None]] = {
    "mandatory_semantic_element": mandatory_semantic_element,
    "coverage_authority_reference": coverage_authority_reference,
    "legacy_false_authority_import": legacy_false_authority_import,
    "ontological_authority": ontological_authority,
    "workflow_execution_identity": workflow_execution_identity,
    "container_contract_copy": container_contract_copy,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("apply", "list"))
    parser.add_argument("defect", nargs="?")
    args = parser.parse_args()
    if args.action == "list":
        print("\n".join(sorted(DEFECTS)))
        return 0
    if not args.defect or args.defect not in DEFECTS:
        parser.error(f"apply requires one of {sorted(DEFECTS)}")
    DEFECTS[args.defect]()
    print(f"B26_P1_CONTROLLED_DEFECT_APPLIED {args.defect}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
