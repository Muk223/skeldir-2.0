#!/usr/bin/env python3
"""
Contract phase gate.

Ensures contract validation, route fidelity tests, and interim semantics
evidence are all passing with empirical artifacts.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from utils import fail, latest_with_prefix, ok, parse_args, require_files  # noqa: E402


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_clean(text: str, label: str) -> None:
    upper = text.upper()
    if "FAIL" in upper or "ERROR" in upper or "TRACEBACK" in upper:
        fail(f"{label} contains failure markers")


def main() -> None:
    args = parse_args()
    root: Path = args.root
    contracts_dir = root / "contracts"

    # Contract validation log
    contract_log = contracts_dir / "contract_validation_log.txt"
    require_files([contract_log])
    cv_text = _load_text(contract_log)
    _assert_clean(cv_text, str(contract_log))
    if "VALIDATION COMPLETE: ALL PASS" not in cv_text.upper():
        fail(f"{contract_log} does not indicate 'Validation Complete: ALL PASS'")
    ok("Contract validation run passed")

    # Route fidelity pytest results
    route_log = contracts_dir / "route_fidelity_log.txt"
    require_files([route_log])
    rf_text = _load_text(route_log)
    _assert_clean(rf_text, str(route_log))
    if "PASSED" not in rf_text.lower():
        fail("Route fidelity log does not indicate tests passed")
    ok("Route fidelity tests passed")

    # Interim semantics probe (SYSTEM_PHASE=B0.1)
    semantics_log = latest_with_prefix(root, "contracts", "interim_semantics_B0.1")
    sem_text = _load_text(semantics_log)
    normalized = sem_text.replace(" ", "").lower()
    if '"verified":false' not in normalized:
        fail(f"{semantics_log} missing verified:false under B0.1")
    if "upgrade_notice" not in normalized:
        fail(f"{semantics_log} missing upgrade_notice in response payload")
    ok(f"Interim semantics evidenced via {semantics_log}")

    ok("Contract phase gate: PASS")


if __name__ == "__main__":
    main()
