#!/usr/bin/env python3
"""Per-proof result ledger for the B14 consolidated lane (anti-severance).

H-P2-11: a wrapper/aggregator can report green despite a missing, cancelled,
stale, or failed child proof. This ledger makes that structurally impossible:

* every proof section records exactly one row (proof id, return code,
  candidate SHA, timestamp) via `--proof ... --return-code ...`;
* `--aggregate` requires ALL eight expected proofs present with return code
  0 AND every expected JUnit file present and parseable with zero
  failures/errors; anything else exits non-zero naming thefirstname missing
  or failed proof.

The ledger is append-only JSONL; the aggregator reads it back and refuses to
adjudicate when rows are missing, duplicated, or bound to different SHAs.
Recording itself never changes a proof verdict (P2-C5): it only observes.

Usage (inside the consolidated job):
    python scripts/ci/b14_record_proof_result.py --proof p0 --return-code "$RC" \\
        --artifacts-dir artifacts/b14_consolidated --sha "$ADJUDICATED_SHA" \\
        --junit artifacts/b14_p0/junit.negative.xml [...]
    python scripts/ci/b14_record_proof_result.py --aggregate \\
        --artifacts-dir artifacts/b14_consolidated --sha "$ADJUDICATED_SHA"
"""
from __future__ import annotations

import argparse
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_PROOFS = ["p0", "p1", "p2", "p3", "p4", "p5", "p6", "p7"]

# JUnit files each proof must emit (relative to the proof's artifact dir).
# Paths mirror the incumbent ci.yml jobs byte-for-byte, relocated under
# artifacts/b14_consolidated/<proof>/.
EXPECTED_JUNIT: dict[str, list[str]] = {
    "p0": ["junit.negative.xml", "junit.lifecycle.xml", "junit.delete_api.xml"],
    "p1": ["junit.runtime.xml"],
    "p2": ["junit.runtime.xml"],
    "p3": ["junit.runtime.xml"],
    "p4": ["junit.runtime.xml"],
    "p5": ["junit.runtime.xml"],
    "p6": ["junit.enforcer.xml"],
    "p7": ["junit.runtime.xml"],
}

LEDGER_NAME = "proof_results.jsonl"


def ledger_path(artifacts_dir: Path) -> Path:
    return artifacts_dir / LEDGER_NAME


def record(artifacts_dir: Path, proof: str, return_code: int, sha: str) -> int:
    if proof not in EXPECTED_PROOFS:
        print(f"B14 ledger REFUSED: unknown proof id {proof!r}", flush=True)
        return 1
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "proof": proof,
        "return_code": int(return_code),
        "sha": sha,
        "recorded_at": int(time.time()),
    }
    with open(ledger_path(artifacts_dir), "a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"B14 ledger recorded proof={proof} rc={return_code} sha={sha[:12]}", flush=True)
    return 0


def _junit_failures(path: Path) -> tuple[int, int, str]:
    """Return (tests, problems, diagnosis) for one JUnit XML file."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return (0, 1, f"unparseable JUnit XML: {exc}")
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites and root.tag != "testsuites":
        suites = [root]
    tests = problems = 0
    failing: list[str] = []
    for s in suites:
        try:
            tests += int(s.get("tests", "0"))
            problems += int(s.get("failures", "0")) + int(s.get("errors", "0"))
        except ValueError:
            return (0, 1, "non-numeric tests/failures/errors attributes")
        for case in s.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failing.append(
                    f"{case.get('classname', '?')}::{case.get('name', '?')}"
                )
    diag = "; ".join(failing[:10])
    return (tests, problems, diag)


def aggregate(artifacts_dir: Path, sha: str) -> int:
    lp = ledger_path(artifacts_dir)
    if not lp.exists():
        print("B14 aggregate RED: ledger missing (no proof recorded)", flush=True)
        return 1
    rows = [json.loads(line) for line in lp.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_proof: dict[str, list[dict]] = {}
    for r in rows:
        by_proof.setdefault(r.get("proof", "?"), []).append(r)

    failures: list[str] = []
    for proof in EXPECTED_PROOFS:
        got = by_proof.get(proof, [])
        if not got:
            failures.append(f"missing-child:{proof}")
            continue
        if len(got) > 1:
            failures.append(f"duplicate-record:{proof}x{len(got)}")
        for r in got:
            if r.get("sha") != sha:
                failures.append(f"wrong-sha:{proof} ({r.get('sha', '?')[:12]} != {sha[:12]})")
            if int(r.get("return_code", 1)) != 0:
                failures.append(f"proof-failed:{proof} rc={r.get('return_code')}")
        # JUnit presence + zero-problem check per proof.
        for rel in EXPECTED_JUNIT[proof]:
            jp = artifacts_dir / proof / rel
            if not jp.exists():
                failures.append(f"missing-artifact:{proof}/{rel}")
                continue
            tests, problems, diag = _junit_failures(jp)
            if problems:
                failures.append(f"junit-failures:{proof}/{rel} problems={problems} {diag}")
            elif tests == 0:
                failures.append(f"junit-empty:{proof}/{rel}")

    if failures:
        print("B14 aggregate RED:", flush=True)
        for f in failures:
            print(f"  - {f}", flush=True)
        return 1
    print(f"B14 aggregate GREEN: 8/8 proofs rc=0, JUnit clean, sha={sha[:12]}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifacts-dir", required=True)
    ap.add_argument("--sha", required=True, help="candidate SHA (ADJUDICATED_SHA)")
    ap.add_argument("--proof", default=None, choices=EXPECTED_PROOFS)
    ap.add_argument("--return-code", type=int, default=None)
    ap.add_argument("--aggregate", action="store_true")
    args = ap.parse_args()

    artifacts = Path(args.artifacts_dir)
    if args.aggregate:
        return aggregate(artifacts, args.sha)
    if args.proof is None or args.return_code is None:
        print("need --proof + --return-code, or --aggregate", flush=True)
        return 2
    return record(artifacts, args.proof, args.return_code, args.sha)


if __name__ == "__main__":
    raise SystemExit(main())
