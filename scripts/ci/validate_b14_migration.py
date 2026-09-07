#!/usr/bin/env python3
"""Monotonic-authority validator for the B14 proof migration (P2-C4, C2-12).

Legal transition (add-before-remove, never weaker at any intermediate state):

    SHADOW: OLD required, NEW shadow (new context absent from contract)
    DUAL:   OLD required + NEW required (both present, both implemented)
    CUTOVER: NEW required, OLD retired (old contexts absent AND old ci.yml
             jobs deleted) -- only with a complete equivalence corpus
    FORBIDDEN: old authority removed before the successor is live/equivalent.

The validator reads the in-repo governance contract plus the workflow tree
(offline-capable) and exits 0 for legal states, 1 with causal diagnosis for
weaker intermediate states. It confers no authority itself (P2-C4, s4.12):
promotion still requires the governed human/admin contract change; this gate
only refuses to bless unlawful ones.

Corpus gate (C2-04/s4.5): --corpus <equivalence evidence JSON> must list
  >=10 pairs, >=3 high-risk (tenant/privacy-relevant), >=2 docs-only,
  >=2 merge_group SHAs, >=1 red-team mutation, all same-SHA, all GREEN.

`--self-test` builds synthetic contract/workflow trees: premature retirement
(Gate 1/3 falsifier) must RED; lawful SHADOW/DUAL/CUTOVER must GREEN.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "contracts-internal" / "governance" / "b03_phase2_required_status_checks.main.json"
WORKFLOWS = REPO / ".github" / "workflows"
SHADOW_WORKFLOW = "b14-privacy-consolidated.yml"

OLD_CONTEXTS = [
    "B1.4 P0 Privacy Authority Lock",
    "B1.4 P1 Ingress Contract Sanitization",
    "B1.4 P2 Session Authority Proofs",
    "B1.4 P3 Attribution Locality Proofs",
    "B1.4 P4 Retention + Deterministic Deletion Proofs",
    "B1.4 P5 Export Log Artifact No-Leak",
    "B1.4 P6 Merge-Blocking Privacy Proof Plane Binding",
    "B1.4 P7 E2E Privacy System Proofs",
]
OLD_JOBS = [
    "b14-p0-privacy-authority-lock",
    "b14-p1-ingress-contract-sanitization",
    "b14-p2-session-authority-proofs",
    "b14-p3-attribution-locality-proofs",
    "b14-p4-retention-deletion-proofs",
    "b14-p5-export-log-artifact-no-leak",
    "b14-p6-proof-plane-binding",
    "b14-p7-e2e-privacy-system-proofs",
]
NEW_CONTEXT = "B1.4 Privacy Consolidated Plane"

CORPUS_MIN = {"pairs": 10, "high_risk": 3, "docs_only": 2, "merge_group": 2, "red_team": 1}


def load_contract(path: Path) -> list[str]:
    return list(json.loads(path.read_text(encoding="utf-8"))["required_contexts"])


def ci_has_old_jobs(workflows: Path) -> list[str]:
    ci = workflows / "ci.yml"
    if not ci.exists():
        return []
    doc = yaml.safe_load(ci.read_text(encoding="utf-8")) or {}
    jobs = doc.get("jobs") or {}
    return [j for j in OLD_JOBS if j in jobs]


def shadow_exists(workflows: Path) -> bool:
    return (workflows / SHADOW_WORKFLOW).exists()


def check_corpus(corpus: dict) -> list[str]:
    problems: list[str] = []
    pairs = corpus.get("pairs", [])
    if len(pairs) < CORPUS_MIN["pairs"]:
        problems.append(f"corpus-too-small:{len(pairs)}<10")
    kinds = [p.get("class") for p in pairs]
    for cls, need in (("high_risk", 3), ("docs_only", 2), ("merge_group", 2), ("red_team", 1)):
        if kinds.count(cls) < need:
            problems.append(f"corpus-missing-class:{cls}")
    for p in pairs:
        if p.get("old_sha") != p.get("new_sha") or p.get("old_sha") != p.get("sha"):
            problems.append(f"corpus-wrong-sha:{p.get('id', '?')}")
        if p.get("verdict") != "GREEN":
            problems.append(f"corpus-not-green:{p.get('id', '?')}")
    return problems


def assess(contract_path: Path, workflows: Path, corpus: dict | None) -> tuple[str, list[str]]:
    """Return (state, problems). Empty problems = lawful."""
    contexts = set(load_contract(contract_path))
    old_in_contract = [c for c in OLD_CONTEXTS if c in contexts]
    new_in_contract = NEW_CONTEXT in contexts
    old_impl = ci_has_old_jobs(workflows)
    shadow = shadow_exists(workflows)
    problems: list[str] = []

    if old_in_contract and not new_in_contract:
        state = "SHADOW" if shadow else "PRE-MIGRATION"
        if not old_impl:
            problems.append("old-impl-missing-while-required (ci.yml jobs deleted before successor live)")
        return state, problems

    if old_in_contract and new_in_contract:
        if not old_impl:
            problems.append("dual-authority-broken: OLD required but ci.yml implementation deleted")
        if not shadow:
            problems.append("dual-authority-broken: NEW required but shadow workflow missing")
        return "DUAL", problems

    if new_in_contract and not old_in_contract:
        # CUTOVER: lawful only with complete corpus AND old impl retired.
        if old_impl:
            problems.append("duplication-not-consolidation: OLD retired from authority but still executes in ci.yml")
        if corpus is None:
            problems.append("premature-retirement: no equivalence corpus (Gate 1/3 falsifier)")
        else:
            problems.extend(check_corpus(corpus))
        return "CUTOVER", problems

    # Neither old nor new: protection strictly weaker than before migration.
    problems.append("authority-severed: all 8 B14 contexts absent and no successor (merge protection weaker)")
    return "SEVERED", problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", default=str(CONTRACT))
    ap.add_argument("--workflows", default=str(WORKFLOWS))
    ap.add_argument("--corpus", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8")) if args.corpus else None
    state, problems = assess(Path(args.contract), Path(args.workflows), corpus)
    if problems:
        print(f"B14 migration RED state={state}", flush=True)
        for p in problems:
            print(f"  - {p}", flush=True)
        return 1
    print(f"B14 migration GREEN state={state}", flush=True)
    return 0


# --- Gate 1/3 active falsifiers ----------------------------------------------

def _write_tree(base: Path, contexts: list[str], ci_jobs: list[str], shadow: bool) -> tuple[Path, Path]:
    gov = base / "gov"
    wf = base / "wf"
    gov.mkdir(parents=True, exist_ok=True)
    wf.mkdir(parents=True, exist_ok=True)
    (gov / "contract.json").write_text(json.dumps({"required_contexts": contexts}), encoding="utf-8")
    jobs = {j: {"runs-on": "ubuntu-latest", "steps": [{"run": "true"}]} for j in ci_jobs}
    (wf / "ci.yml").write_text(yaml.safe_dump({"name": "CI", "jobs": jobs}), encoding="utf-8")
    if shadow:
        (wf / SHADOW_WORKFLOW).write_text("name: shadow\n", encoding="utf-8")
    return gov / "contract.json", wf


def _corpus(n: int = 10) -> dict:
    pairs = []
    classes = (["high_risk"] * 3 + ["docs_only"] * 2 + ["merge_group"] * 2
               + ["red_team"] + ["ordinary"] * 2)
    for i in range(n):
        sha = f"{i:040d}"
        pairs.append({"id": f"p{i}", "class": classes[i], "sha": sha,
                      "old_sha": sha, "new_sha": sha, "verdict": "GREEN"})
    return {"pairs": pairs}


def self_test() -> int:
    passed = failed = 0

    def run_case(name: str, want_ok: bool, contexts: list[str],
                 ci_jobs: list[str], shadow: bool, corpus=None) -> None:
        nonlocal passed, failed
        with tempfile.TemporaryDirectory() as tmp:
            cp, wf = _write_tree(Path(tmp), contexts, ci_jobs, shadow)
            state, problems = assess(cp, wf, corpus)
            ok = not problems
            good = (ok == want_ok)
            print(f"  {'PASS' if good else 'FAIL'}  {name} "
                  f"(state={state} want_ok={want_ok} got_ok={ok})", flush=True)
            if not good:
                for p in problems:
                    print(f"      - {p}", flush=True)
            passed, failed = passed + good, failed + (not good)

    print("B14 migration self-test (Gate 1/3 falsifiers):", flush=True)
    run_case("pre-migration", True, OLD_CONTEXTS, OLD_JOBS, False)
    run_case("shadow", True, OLD_CONTEXTS, OLD_JOBS, True)
    run_case("dual", True, OLD_CONTEXTS + [NEW_CONTEXT], OLD_JOBS, True)
    run_case("cutover-lawful", True, [NEW_CONTEXT], [], True, _corpus())
    # Active falsifier: remove OLD before NEW is live/equivalent.
    run_case("premature-retirement-no-corpus", False, [NEW_CONTEXT], [], True, None)
    run_case("premature-retirement-thin-corpus", False, [NEW_CONTEXT], [], True, _corpus(4))
    run_case("severed", False, [], [], True, None)
    run_case("duplication", False, [NEW_CONTEXT], OLD_JOBS, True, _corpus())
    run_case("dual-impl-deleted", False, OLD_CONTEXTS + [NEW_CONTEXT], [], True, None)

    print(f"B14 migration self-test: {passed} passed, {failed} failed", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
