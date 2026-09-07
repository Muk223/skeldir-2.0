#!/usr/bin/env python3
"""Negative controls for the B14 consolidation machinery (Gate 4, C2-06).

A migration gate never observed failing is not load-bearing evidence. Each
control below drives one piece of Phase II machinery into a precise failure
and asserts it refuses, then repairs and asserts it accepts. Covers:

  comparator  C2-06 1-7 + altered-test-set + omitted-NC (via --self-test)
  migration   Gate 1/3 premature-retirement falsifier (via --self-test)
  aggregator  missing-child / failed-child / wrong-SHA / duplicate (H-P2-11)
  env-sig     foreign-state refusal + miss rebuild (Gate 2/7)
  provisioner DSN rewriting unit (P2-C6 isolation addressing)

Run:  python scripts/ci/test_b14_consolidation_negative_controls.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CI = REPO / "scripts" / "ci"

passed = failed = 0


def check(name: str, good: bool, detail: str = "") -> None:
    global passed, failed
    print(f"  {'PASS' if good else 'FAIL'}  {name}" + (f" ({detail})" if detail and not good else ""),
          flush=True)
    passed, failed = passed + good, failed + (not good)


def run_script(name: str, *args: str) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(CI / name), *args],
                          cwd=REPO, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def junit(path: Path, names: list[str], failing: list[str] = []) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cases = "".join(
        f'<testcase classname="t" name="{n}"/>'
        if n not in failing else
        f'<testcase classname="t" name="{n}"><failure>x</failure></testcase>'
        for n in names)
    path.write_text(
        f'<?xml version="1.0"?><testsuite tests="{len(names)}" '
        f'failures="{len(failing)}" errors="0">'
        + cases + "</testsuite>", encoding="utf-8")


def main() -> int:
    print("B14 consolidation negative controls:", flush=True)

    rc, _ = run_script("compare_b14_equivalence.py", "--self-test")
    check("comparator-C2-06-corpus", rc == 0, f"rc={rc}")

    rc, _ = run_script("validate_b14_migration.py", "--self-test")
    check("migration-gate-falsifiers", rc == 0, f"rc={rc}")

    # --- aggregator (H-P2-11 wrapper severance) ---
    sys.path.insert(0, str(CI))
    from b14_record_proof_result import (EXPECTED_JUNIT, EXPECTED_PROOFS,
                                         aggregate, record)
    sha = "d" * 40
    with tempfile.TemporaryDirectory() as tmp:
        art = Path(tmp) / "a"
        # missing-child: 7/8 recorded must RED.
        for p in EXPECTED_PROOFS[:7]:
            record(art, p, 0, sha)
            for rel in EXPECTED_JUNIT[p]:
                junit(art / p / rel, ["t::x"])
        check("aggregator-missing-child-RED", aggregate(art, sha) != 0)
        # repair: 8/8 clean must GREEN.
        record(art, "p7", 0, sha)
        for rel in EXPECTED_JUNIT["p7"]:
            junit(art / "p7" / rel, ["t::x"])
        check("aggregator-full-GREEN", aggregate(art, sha) == 0)
        # failed-child must RED naming the proof.
        record(art, "p3", 1, sha)
        check("aggregator-failed-child-RED", aggregate(art, sha) != 0)
        # wrong-SHA ledger must RED (stale artifact).
        with tempfile.TemporaryDirectory() as tmp2:
            art2 = Path(tmp2) / "b"
            for p in EXPECTED_PROOFS:
                record(art2, p, 0, "e" * 40)
                for rel in EXPECTED_JUNIT[p]:
                    junit(art2 / p / rel, ["t::x"])
            check("aggregator-stale-sha-RED", aggregate(art2, sha) != 0)

    # JUnit with a failing case must RED the aggregate even with rc=0
    # recorded (ledger cannot launder a red child).
    with tempfile.TemporaryDirectory() as tmp:
        art = Path(tmp) / "c"
        for p in EXPECTED_PROOFS:
            record(art, p, 0, sha)
            for rel in EXPECTED_JUNIT[p]:
                junit(art / p / rel, ["t::x"],
                      failing=["t::x"] if p == "p1" and rel == "junit.runtime.xml" else [])
        check("aggregator-junit-red-RED", aggregate(art, sha) != 0)

    # --- env-sig foreign state (Gate 7) ---
    from b14_env_signature import compute_signature
    sig = compute_signature()
    check("envsig-binds-169-migrations",
          sig["db_schema_authority"]["revision_count"] == 169,
          str(sig["db_schema_authority"]["revision_count"]))
    with tempfile.TemporaryDirectory() as tmp:
        sp = Path(tmp) / "sig.json"
        sp.write_text(json.dumps(sig), encoding="utf-8")
        rc, _ = run_script("b14_env_signature.py", "--check", str(sp))
        check("envsig-check-GREEN", rc == 0, f"rc={rc}")
        # Foreign state (validly-addressable but semantically different
        # dependency authority) must be refused.
        foreign = json.loads(sp.read_text(encoding="utf-8"))
        foreign["dependency_authority"]["backend/requirements.txt"] = "0" * 64
        fp = Path(tmp) / "foreign.json"
        fp.write_text(json.dumps(foreign), encoding="utf-8")
        rc, _ = run_script("b14_env_signature.py", "--check", str(fp))
        check("envsig-foreign-state-RED", rc != 0, f"rc={rc}")

    # --- provisioner DSN addressing (P2-C6) ---
    from b14_provision_template_dbs import PROOF_DBS, dsn_for
    m = "postgresql://postgres:postgres@127.0.0.1:5432/postgres"
    dsns = {p: dsn_for(m, db) for p, db in PROOF_DBS.items()}
    check("provisioner-7-isolated-dbs", len(set(dsns.values())) == 7, str(len(set(dsns.values()))))
    check("provisioner-no-shared-consequence-db",
          all("b14_p" in d and d != m for d in dsns.values()))
    check("provisioner-p6-stateless", "p6" not in PROOF_DBS)

    print(f"B14 consolidation negative controls: {passed} passed, {failed} failed", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
