#!/usr/bin/env python3
"""Old/new equivalence comparator for the B14 consolidated lane (P2-C2, C2-04/05/06).

 Compares incumbent (8-job, ci.yml) proof against the consolidated shadow lane
 on the SAME candidate SHA. Verdict-only equality is inadmissible (H-P2-07):
 the comparator binds candidate SHA, proof-family identity, governed test
 identities, negative-control evidence, semantic verdict, failure class, and
 environment authority.

 Layouts:
   --old-dir  directory holding the 8 incumbent artifact uploads
              (b14-p0-runtime-artifacts/..., ...., b14_p0/... accepted too)
   --new-dir  consolidated artifacts dir (artifacts/b14_consolidated)

 Verdicts:
   --old-conclusions '{"p0":"success",...}' (live check-run conclusions; when
     absent, derived from JUnit and flagged partial)
   new verdict comes from proof_results.jsonl + JUnit in --new-dir.

 Exit 0 (GREEN) iff every check passes; exit 1 (RED) with causal diagnosis.
 `--self-test` runs the C2-06 non-vacuity corpus (7 required controls plus
 altered-test-set and omitted-NC) and fails unless every control REDs
 precisely and the repaired tree GREENs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "ci"))
from b14_env_signature import compute_signature  # noqa: E402
from b14_record_proof_result import EXPECTED_JUNIT, EXPECTED_PROOFS  # noqa: E402

OLD_SUBDIRS = {
    "p0": ["b14-p0-runtime-artifacts", "b14_p0"],
    "p1": ["b14-p1-runtime-artifacts", "b14_p1"],
    "p2": ["b14-p2-runtime-artifacts", "b14_p2"],
    "p3": ["b14-p3-runtime-artifacts", "b14_p3"],
    "p4": ["b14-p4-runtime-artifacts", "b14_p4"],
    "p5": ["b14-p5-runtime-artifacts", "b14_p5"],
    "p6": ["b14-p6-runtime-artifacts", "b14_p6"],
    "p7": ["b14-p7-runtime-artifacts", "b14_p7"],
}

# NC evidence files that must exist on both sides (paths relative to proof dir).
NC_EVIDENCE = {
    "p6": ["proof_plane_report.json"],
    "p7": ["p7_composed_runtime_report.json", "p7_negative_controls_report.json"],
}


def _find_old_proof_dir(old_dir: Path, proof: str) -> Path | None:
    for cand in OLD_SUBDIRS[proof]:
        p = old_dir / cand
        if p.is_dir():
            return p
    return None


def parse_junit(path: Path) -> dict:
    """Canonical semantic identity of a JUnit file (timestamps stripped)."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {"ok": False, "diagnosis": f"unparseable:{exc}"}
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return {"ok": False, "diagnosis": "no-testsuite"}
    ids: list[str] = []
    failing: list[str] = []
    tests = failures = errors = skipped = 0
    for s in suites:
        try:
            tests += int(s.get("tests", "0"))
            failures += int(s.get("failures", "0"))
            errors += int(s.get("errors", "0"))
            skipped += int(s.get("skipped", "0"))
        except ValueError:
            return {"ok": False, "diagnosis": "non-numeric-counters"}
        for case in s.iter("testcase"):
            nid = f"{case.get('classname', '?')}::{case.get('name', '?')}"
            ids.append(nid)
            if case.find("failure") is not None or case.find("error") is not None:
                failing.append(nid)
    return {
        "ok": True,
        "tests": tests,
        "problems": failures + errors,
        "skipped": skipped,
        "ids": sorted(ids),
        "failing": sorted(failing),
        "green": (failures + errors) == 0 and tests > 0,
    }


def compare(old_dir: Path, new_dir: Path, sha: str,
            old_sha: str, new_sha: str,
            old_conclusions: dict | None) -> tuple[bool, list[str], dict]:
    checks: list[str] = []
    ok = True

    def fail(msg: str) -> None:
        nonlocal ok
        ok = False
        checks.append(f"RED {msg}")

    def past(msg: str) -> None:
        checks.append(f"GREEN {msg}")

    # --- C2-05 same-SHA binding ---
    if not (old_sha == new_sha == sha):
        fail(f"wrong-sha: old={old_sha[:12]} new={new_sha[:12]} claimed={sha[:12]}")
        return ok, checks, {}
    past(f"same-sha:{sha[:12]}")

    # --- new-side ledger (anti-severance evidence) ---
    ledger = new_dir / "proof_results.jsonl"
    if not ledger.exists():
        fail("missing-new-proof: ledger proof_results.jsonl absent")
        return ok, checks, {}
    ledger_rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    new_rc = {r["proof"]: int(r["return_code"]) for r in ledger_rows}
    for r in ledger_rows:
        if r.get("sha") != sha:
            fail(f"stale-artifact: ledger row {r.get('proof')} sha={str(r.get('sha'))[:12]}")
    if not ok:
        return ok, checks, {}

    corpus: dict[str, dict] = {}
    for proof in EXPECTED_PROOFS:
        old_pd = _find_old_proof_dir(old_dir, proof)
        if old_pd is None:
            fail(f"missing-old-proof:{proof}")
            continue
        new_pd = new_dir / proof
        if not new_pd.is_dir():
            fail(f"missing-new-proof:{proof}")
            continue
        if proof not in new_rc:
            fail(f"missing-new-proof:{proof} (no ledger row)")
            continue

        # Governed test identities + semantic verdict per JUnit file.
        file_rows: list[dict[str, Any]] = []
        for rel in EXPECTED_JUNIT[proof]:
            oj, nj = old_pd / rel, new_pd / rel
            if not oj.exists():
                fail(f"missing-old-proof:{proof}/{rel}")
                continue
            if not nj.exists():
                fail(f"missing-new-proof:{proof}/{rel}")
                continue
            o, n = parse_junit(oj), parse_junit(nj)
            if not o["ok"]:
                fail(f"missing-old-proof:{proof}/{rel} ({o['diagnosis']})")
                continue
            if not n["ok"]:
                fail(f"missing-new-proof:{proof}/{rel} ({n['diagnosis']})")
                continue
            if o["ids"] != n["ids"]:
                only_old = sorted(set(o["ids"]) - set(n["ids"]))
                only_new = sorted(set(n["ids"]) - set(o["ids"]))
                fail(f"altered-test-set:{proof}/{rel} "
                     f"old-only={only_old[:3]} new-only={only_new[:3]}")
                continue
            past(f"test-identity:{proof}/{rel} n={len(n['ids'])}")
            # Verdict + failure-class equivalence.
            if o["green"] != n["green"]:
                direction = "green-old/red-new" if o["green"] else "red-old/green-new"
                fail(f"divergence:{direction} {proof}/{rel}")
                continue
            if not o["green"] and o["failing"] != n["failing"]:
                fail(f"failure-class-mismatch:{proof}/{rel} "
                     f"old={o['failing'][:3]} new={n['failing'][:3]}")
                continue
            past(f"verdict:{proof}/{rel} {'green' if n['green'] else 'red-matched'}")
            file_rows.append({"file": rel, "old": o, "new": n})

        # Ledger rc must agree with JUnit verdict in the wrapper-green direction:
        # rc==0 with red JUnit is wrapper-green-over-red-child (H-P2-11). The
        # reverse (rc!=0 with green JUnit) is legitimate: enforcer and
        # negative-control steps emit no JUnit but fail the section by rc.
        junit_red = any(not r["new"]["green"] for r in file_rows)
        if new_rc[proof] == 0 and junit_red and file_rows:
            fail(f"ledger-junit-mismatch:{proof} rc=0 over red junit")
        # Live conclusions, when supplied, must agree with artifacts.
        # Proof-level verdict binds enforcer/negative-control steps that emit
        # no JUnit: new_green requires ledger rc==0 AND clean JUnit.
        new_green = (new_rc[proof] == 0) and all(
            r["new"]["green"] for r in file_rows) and bool(file_rows)
        if old_conclusions and proof in old_conclusions:
            live_green = old_conclusions[proof] == "success"
            art_green = all(r["old"]["green"] for r in file_rows)
            if live_green != art_green and file_rows:
                fail(f"old-conclusion-mismatch:{proof} live={old_conclusions[proof]}")
            if live_green != new_green:
                direction = ("green-old/red-new" if live_green
                             else "red-old/green-new")
                fail(f"divergence:{direction} {proof} (proof-level)")
            else:
                past(f"proof-verdict:{proof} {'green' if new_green else 'red-matched'}")
        elif not file_rows:
            pass
        else:
            checks.append(f"NOTE verdict-partial:{proof} "
                          f"(no live conclusions; JUnit-only)")

        # Negative-control evidence presence (both sides).
        for rel in NC_EVIDENCE.get(proof, []):
            if not (old_pd / rel).exists():
                fail(f"omitted-negative-control:old {proof}/{rel}")
            if not (new_pd / rel).exists():
                fail(f"omitted-negative-control:new {proof}/{rel}")
        corpus[proof] = {"files": file_rows, "new_rc": new_rc[proof]}

    # --- environment authority (Gate 2/7) ---
    sig_path = new_dir / "env_signature.json"
    if not sig_path.exists():
        fail("missing-new-proof:env_signature.json")
    else:
        try:
            recorded = json.loads(sig_path.read_text(encoding="utf-8"))
            fresh = compute_signature()
            if recorded.get("digest") != fresh.get("digest") and recorded.get("lane_version") == fresh.get("lane_version"):
                # Same lane version but different digest = foreign/stale substrate.
                fail("stale-artifact: env_signature digest != recomputed")
            else:
                past(f"env-authority:{recorded.get('digest', '?')[:12]}")
        except Exception as exc:
            fail(f"missing-new-proof:env_signature unreadable ({exc})")

    return ok, checks, corpus


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--old-dir", default=None)
    ap.add_argument("--new-dir", default=None)
    ap.add_argument("--sha", default=None)
    ap.add_argument("--old-sha", default=None)
    ap.add_argument("--new-sha", default=None)
    ap.add_argument("--old-conclusions", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not all([args.old_dir, args.new_dir, args.sha, args.old_sha, args.new_sha]):
        print("need --old-dir --new-dir --sha --old-sha --new-sha", flush=True)
        return 2
    conc = json.loads(args.old_conclusions) if args.old_conclusions else None
    ok, checks, _ = compare(Path(args.old_dir), Path(args.new_dir),
                            args.sha, args.old_sha, args.new_sha, conc)
    print(f"B14 equivalence {'GREEN' if ok else 'RED'} sha={args.sha[:12]}", flush=True)
    for c in checks:
        print(f"  {c}", flush=True)
    return 0 if ok else 1


# --- C2-06 non-vacuity corpus -------------------------------------------------

def _write_junit(path: Path, ids: list[str], failing: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cases = []
    for nid in ids:
        cls, _, name = nid.partition("::")
        if nid in failing:
            cases.append(
                f'<testcase classname="{cls}" name="{name}">'
                f"<failure>synthetic</failure></testcase>")
        else:
            cases.append(f'<testcase classname="{cls}" name="{name}"/>')
    path.write_text(
        f'<?xml version="1.0"?><testsuite tests="{len(ids)}" '
        f'failures="{len(failing)}" errors="0" skipped="0">'
        + "".join(cases) + "</testsuite>", encoding="utf-8")


IDS_P0 = ["t.Test::test_a", "t.Test::test_b"]
IDS_P1 = ["u.Test::test_c"]


def _fixture(base: Path, sha: str, new_failing_p0: list[str] | None = None,
             old_failing_p0: list[str] | None = None) -> tuple[Path, Path]:
    """Build a minimal 8-proof pair fixture (p0+p1 carry JUnit; rest stubbed)."""
    new = base / "new"
    shutil.rmtree(base, ignore_errors=True)
    for proof in EXPECTED_PROOFS:
        for rel in EXPECTED_JUNIT[proof]:
            ids = IDS_P0 if proof == "p0" else IDS_P1
            of = old_failing_p0 if proof == "p0" else []
            nf = new_failing_p0 if proof == "p0" else []
            op = base / "old" / OLD_SUBDIRS[proof][0] / rel
            np = new / proof / rel
            _write_junit(op, ids, of or [])
            _write_junit(np, ids, nf or [])
    for proof, rels in NC_EVIDENCE.items():
        for rel in rels:
            (base / "old" / OLD_SUBDIRS[proof][0] / rel).parent.mkdir(parents=True, exist_ok=True)
            (base / "old" / OLD_SUBDIRS[proof][0] / rel).write_text("{}", encoding="utf-8")
            (new / proof / rel).parent.mkdir(parents=True, exist_ok=True)
            (new / proof / rel).write_text("{}", encoding="utf-8")
    rows = [{"proof": p, "return_code": 0, "sha": sha, "recorded_at": 1}
            for p in EXPECTED_PROOFS]
    if new_failing_p0:
        rows = [r if r["proof"] != "p0" else {**r, "return_code": 1} for r in rows]
    (new / "proof_results.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n", encoding="utf-8")
    sig = compute_signature()
    (new / "env_signature.json").write_text(json.dumps(sig, indent=2), encoding="utf-8")
    return base / "old", new


def self_test() -> int:
    sha = "a" * 40
    passed = failed = 0

    def run_case(name: str, want_ok: bool, old: Path, new: Path,
                 old_sha: str, new_sha: str, claim: str) -> None:
        nonlocal passed, failed
        ok, checks, _ = compare(old, new, claim, old_sha, new_sha, None)
        good = (ok == want_ok)
        # A RED must carry causal diagnosis, not bare failure.
        if not want_ok and ok is False:
            good = good and any(c.startswith("RED ") for c in checks)
        print(f"  {'PASS' if good else 'FAIL'}  {name} "
              f"(want_ok={want_ok} got_ok={ok})", flush=True)
        if not good:
            for c in checks:
                print(f"      {c}", flush=True)
        passed, failed = passed + good, failed + (not good)

    print("B14 comparator self-test (C2-06 corpus):", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)

        def fresh(sub: str) -> tuple[Path, Path]:
            return _fixture(t / sub, sha)

        old, new = fresh("base")
        run_case("green-pair", True, old, new, sha, sha, sha)

        old, new = fresh("wrongsha")
        run_case("wrong-sha", False, old, new, sha, sha, "b" * 40)

        old, new = fresh("missingold")
        shutil.rmtree(old / "b14-p1-runtime-artifacts")
        run_case("missing-old-proof", False, old, new, sha, sha, sha)

        old, new = fresh("missingnew")
        shutil.rmtree(new / "p2")
        run_case("missing-new-proof", False, old, new, sha, sha, sha)

        # green-old / red-new: new p0 fails the same test the old passes,
        # ledger rc agrees (rc=1).
        old, new = fresh("greenred-src")
        _, new_red = _fixture(t / "greenred-red", sha,
                              new_failing_p0=["t.Test::test_a"])
        shutil.rmtree(new / "p0")
        shutil.copytree(new_red / "p0", new / "p0")
        shutil.copy(new_red / "proof_results.jsonl", new / "proof_results.jsonl")
        run_case("green-old/red-new", False, old, new, sha, sha, sha)

        # red-old / green-new: old p0 fails, new passes.
        old, new = _fixture(t / "redgreen", sha,
                            old_failing_p0=["t.Test::test_a"])
        run_case("red-old/green-new", False, old, new, sha, sha, sha)

        old, new = fresh("stale")
        (new / "proof_results.jsonl").write_text(
            "\n".join(json.dumps({"proof": p, "return_code": 0,
                                  "sha": "c" * 40, "recorded_at": 1},
                                 sort_keys=True) for p in EXPECTED_PROOFS) + "\n",
            encoding="utf-8")
        run_case("stale-artifact", False, old, new, sha, sha, sha)

        old, new = fresh("altered")
        _write_junit(new / "p0" / "junit.negative.xml", ["t.Test::test_a"], [])
        run_case("altered-test-set", False, old, new, sha, sha, sha)

        old, new = fresh("omittednc")
        (new / "p6" / "proof_plane_report.json").unlink()
        run_case("omitted-negative-control", False, old, new, sha, sha, sha)

    print(f"B14 comparator self-test: {passed} passed, {failed} failed", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
