#!/usr/bin/env python3
"""B2.6-P1 pristine -> defect RED -> exact restore -> GREEN battery."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
VALIDATOR = ROOT / "scripts/ci/validate_b26_p1_authority.py"
MUTATOR = ROOT / "scripts/ci/_b26_p1_controlled_defect.py"
CONTRACT = ROOT / "contracts/reconciliation/b2.6/semantic-authority.v1.yaml"
SEMANTIC_MODULE = ROOT / "backend/app/finance_reconciliation/semantic_contract.py"
WORKFLOW = ROOT / ".github/workflows/b2_6-p1-finance-reconciliation-adjudication.yml"

STATIC_CONTROLS = (
    ("mandatory_semantic_element", CONTRACT, "semantic_contract_refused"),
    ("coverage_authority_reference", CONTRACT, "semantic_contract_refused"),
    ("legacy_false_authority_import", SEMANTIC_MODULE, "b26_false_authority_import"),
    ("ontological_authority", CONTRACT, "semantic_contract_refused"),
    ("workflow_execution_identity", WORKFLOW, "b26_required_context_event_identity_ambiguous"),
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _validator() -> subprocess.CompletedProcess[str]:
    return _run(sys.executable, str(VALIDATOR))


def _proof_identity_control() -> dict[str, Any]:
    from scripts.ci.adjudicate_b26_p1_proof_plane import (  # noqa: PLC0415
        AdjudicationError,
        adjudicate,
    )
    from scripts.ci.b26_p1_evidence import (  # noqa: PLC0415
        canonical_json,
        git_identity,
        write_evidence_cell,
    )

    sha, tree = git_identity()
    workflow = "B2.6-P1 Contract Authority, Semantic Freeze and Proof Plane"
    event = "pull_request"
    run_id = "negative-control-local"
    specs: tuple[tuple[str, str, str, str, dict[str, Any]], ...] = (
        (
            "B26-P1-G4-SEMANTIC-AUTHORITY",
            "b26-p1-static-authority",
            "semantic-authority-pristine",
            "B26-P1-NC-01-through-04",
            {},
        ),
        (
            "B26-P1-G8-EXECUTION-IDENTITY",
            "b26-p1-static-authority",
            "governing-workflow-pristine",
            "B26-P1-NC-05",
            {},
        ),
        (
            "B26-P1-G9-NEGATIVE-CONTROLS",
            "b26-p1-static-authority",
            "red-restore-green-ledger",
            "B26-P1-NC-01-through-06",
            {},
        ),
        (
            "B26-P1-G3-G10-CONTAINER-EQUIVALENCE",
            "b26-p1-container-equivalence",
            "candidate-production-image",
            "B26-P1-NC-07",
            {},
        ),
        (
            "B26-P1-G1-G2-INHERITED-PHYSICS",
            "b26-p1-inherited-conduction",
            "b25-p13-context-robust-production-closure",
            "inherited-C19-C20-C21-negative-controls",
            {
                "source_event": event,
                "source_sha": sha,
                "required_jobs": {
                    "B2.5-P13 C19 Context-Robust Production Closure": "success",
                    "B2.5-P13 C20 Verdict Authority Conservation": "success",
                    "B2.5-P13 C21 Freshness and Issuance Authority Conservation": "success",
                    "B2.5-P14 Downstream Projection Safety": "success",
                },
            },
        ),
    )
    with tempfile.TemporaryDirectory(prefix="b26-p1-proof-") as directory:
        root = Path(directory)
        for gate, producer, scenario, falsifier, details in specs:
            write_evidence_cell(
                root / f"{gate}.json",
                gate_id=gate,
                producer=producer,
                scenario_id=scenario,
                falsifier_id=falsifier,
                details=details,
                event_type=event,
                run_id=run_id,
                workflow=workflow,
            )
        adjudicate(
            artifact_root=root,
            candidate_sha=sha,
            candidate_tree=tree,
            event_type=event,
            run_id=run_id,
            workflow=workflow,
        )
        target = root / "B26-P1-G4-SEMANTIC-AUTHORITY.json"
        pristine = target.read_bytes()
        cell = json.loads(pristine)
        cell["candidate_sha"] = "0" * 40
        unhashed = {key: value for key, value in cell.items() if key != "artifact_hash"}
        cell["artifact_hash"] = hashlib.sha256(canonical_json(unhashed)).hexdigest()
        target.write_text(json.dumps(cell, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            adjudicate(
                artifact_root=root,
                candidate_sha=sha,
                candidate_tree=tree,
                event_type=event,
                run_id=run_id,
                workflow=workflow,
            )
        except AdjudicationError as exc:
            observed_red = str(exc)
        else:
            raise RuntimeError("proof_identity_control_did_not_turn_red")
        target.write_bytes(pristine)
        adjudicate(
            artifact_root=root,
            candidate_sha=sha,
            candidate_tree=tree,
            event_type=event,
            run_id=run_id,
            workflow=workflow,
        )
    return {
        "control": "proof_candidate_identity",
        "pristine_hash": _sha(pristine),
        "observed_red": observed_red,
        "restoration_hash": _sha(pristine),
        "restored_green": True,
    }


def run_battery() -> list[dict[str, Any]]:
    pristine = _validator()
    if pristine.returncode != 0:
        raise RuntimeError(f"pristine_validator_red:{pristine.stdout}{pristine.stderr}")
    ledger: list[dict[str, Any]] = []
    for defect, target, expected_red in STATIC_CONTROLS:
        original = target.read_bytes()
        pristine_hash = _sha(original)
        try:
            applied = _run(sys.executable, str(MUTATOR), "apply", defect)
            if applied.returncode != 0:
                raise RuntimeError(f"mutator_failed:{defect}:{applied.stdout}{applied.stderr}")
            red = _validator()
            red_text = red.stdout + red.stderr
            if red.returncode == 0 or expected_red not in red_text:
                raise RuntimeError(f"control_did_not_red:{defect}:{red_text}")
        finally:
            target.write_bytes(original)
        if _sha(target.read_bytes()) != pristine_hash:
            raise RuntimeError(f"restore_hash_mismatch:{defect}")
        green = _validator()
        if green.returncode != 0:
            raise RuntimeError(f"restore_not_green:{defect}:{green.stdout}{green.stderr}")
        ledger.append(
            {
                "control": defect,
                "pristine_hash": pristine_hash,
                "observed_red": expected_red,
                "restoration_hash": _sha(target.read_bytes()),
                "restored_green": True,
            }
        )
    ledger.append(_proof_identity_control())
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    try:
        ledger = run_battery()
    except RuntimeError as exc:
        print(f"B26_P1_NEGATIVE_CONTROLS_FAIL {exc}")
        return 1
    if args.evidence_out:
        from scripts.ci.b26_p1_evidence import write_evidence_cell  # noqa: PLC0415

        write_evidence_cell(
            args.evidence_out,
            gate_id="B26-P1-G9-NEGATIVE-CONTROLS",
            producer="b26-p1-static-authority",
            scenario_id="red-restore-green-ledger",
            falsifier_id="B26-P1-NC-01-through-06",
            details={"controls": ledger, "control_count": len(ledger)},
        )
    print("B26_P1_NEGATIVE_CONTROLS_PASS")
    print(json.dumps(ledger, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
