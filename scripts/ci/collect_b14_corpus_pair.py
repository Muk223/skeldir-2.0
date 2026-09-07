#!/usr/bin/env python3
"""Collect one same-SHA paired corpus record for the B14 migration (s4.5).

For a PR/merge_group candidate SHA, binds the incumbent ci.yml B14 jobs
(old run) with the consolidated shadow job (new run): check conclusions,
per-job queue/execution times, and run identifiers. Appends a pair record to
a corpus JSON file shaped for `validate_b14_migration.py --corpus` (extra
detail fields are preserved and ignored by the gate).

Artifact-download + JUnit comparison is NOT done here: run
`compare_b14_equivalence.py` on the downloaded artifact trees and store its
verdict in the pair's `comparator` field (GREEN required for promotion).

Usage:
    python scripts/ci/collect_b14_corpus_pair.py --sha <sha> --event pull_request \\
        --class ordinary --old-run 34140547082 --new-run 34140547236 \\
        --corpus docs/forensics/p2_b14_equivalence_corpus.json

Pair classes: ordinary | high_risk | docs_only | merge_group | red_team.
Requires `gh` (read-only API use; never mutates authority).
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

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
NEW_CONTEXT = "B1.4 Privacy Consolidated Plane"

OLD_JOB_IDS = [
    "b14-p0-privacy-authority-lock",
    "b14-p1-ingress-contract-sanitization",
    "b14-p2-session-authority-proofs",
    "b14-p3-attribution-locality-proofs",
    "b14-p4-retention-deletion-proofs",
    "b14-p5-export-log-artifact-no-leak",
    "b14-p6-proof-plane-binding",
    "b14-p7-e2e-privacy-system-proofs",
]
NEW_JOB_ID = "b14-privacy-consolidated"


def gh_api(*args: str) -> object:
    proc = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api failed: {' '.join(args)}: {proc.stderr[:300]}")
    out = (proc.stdout or "").strip()
    # gh --jq on a scalar emits raw text (unquoted); parse JSON when possible.
    try:
        return json.loads(out or "null")
    except json.JSONDecodeError:
        return out


def iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def run_created_at(run_id: str) -> datetime:
    data = gh_api(f"repos/:owner/:repo/actions/runs/{run_id}", "--jq", ".created_at")
    return iso(str(data))


def _iter_pages(proc: subprocess.CompletedProcess[str]) -> Any:
    """Yield decoded JSON docs from possibly-concatenated gh --paginate output."""
    text = proc.stdout or ""
    decoder = json.JSONDecoder()
    idx, n = 0, len(text)
    while idx < n:
        while idx < n and text[idx].isspace():
            idx += 1
        if idx >= n:
            break
        doc, idx = decoder.raw_decode(text, idx)
        yield doc


def run_jobs(run_id: str) -> list[dict]:
    proc = subprocess.run(
        ["gh", "api", f"repos/:owner/:repo/actions/runs/{run_id}/jobs",
         "--paginate"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh jobs failed for run {run_id}: {proc.stderr[:300]}")
    jobs: list[dict] = []
    for data in _iter_pages(proc):
        if isinstance(data, dict):
            jobs.extend(data.get("jobs", []))
    return jobs


def check_conclusions(sha: str) -> dict[str, str]:
    """Map check-run name -> conclusion for the candidate SHA (all pages)."""
    proc = subprocess.run(
        ["gh", "api", f"repos/:owner/:repo/commits/{sha}/check-runs",
         "--paginate"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh check-runs failed for {sha[:12]}: {proc.stderr[:300]}")
    out: dict[str, str] = {}
    for data in _iter_pages(proc):
        if isinstance(data, dict):
            for cr in data.get("check_runs", []):
                out.setdefault(str(cr.get("name")), str(cr.get("conclusion")))
    return out


def job_timing(jobs: list[dict], wanted: list[str], created: datetime) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for j in jobs:
        name = str(j.get("name"))
        jid = str(j.get("id"))
        key = None
        for w in wanted:
            if name == w or jid == w or name.endswith(w):
                key = w
                break
        if key is None or key in found:
            continue
        try:
            start, done = iso(j["started_at"]), iso(j["completed_at"])
            found[key] = {
                "job_id": jid,
                "conclusion": j.get("conclusion"),
                "queue_s": max(0.0, (start - created).total_seconds()),
                "exec_s": max(0.0, (done - start).total_seconds()),
            }
        except (KeyError, ValueError, TypeError):
            found[key] = {"job_id": jid, "conclusion": j.get("conclusion"),
                          "queue_s": None, "exec_s": None}
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--event", required=True)
    ap.add_argument("--class", dest="cls", required=True,
                    choices=("ordinary", "high_risk", "docs_only", "merge_group", "red_team"))
    ap.add_argument("--old-run", required=True)
    ap.add_argument("--new-run", required=True)
    ap.add_argument("--corpus", required=True)
    args = ap.parse_args()

    old_created = run_created_at(args.old_run)
    new_created = run_created_at(args.new_run)
    old_jobs = run_jobs(args.old_run)
    new_jobs = run_jobs(args.new_run)
    # The jobs API reports display names (job `name:`), not YAML job ids.
    old_t = job_timing(old_jobs, OLD_CONTEXTS, old_created)
    new_t = job_timing(new_jobs, [NEW_CONTEXT], new_created)
    conclusions = check_conclusions(args.sha)

    missing_old = [c for c in OLD_CONTEXTS if conclusions.get(c) != "success"]
    new_conclusion = conclusions.get(NEW_CONTEXT)
    verdict = "GREEN" if (not missing_old and new_conclusion == "success") else "PENDING"

    pair = {
        "id": f"{args.event}-{args.sha[:12]}",
        "class": args.cls,
        "event": args.event,
        "sha": args.sha,
        "old_sha": args.sha,
        "new_sha": args.sha,
        "old_run": args.old_run,
        "new_run": args.new_run,
        "old_conclusions": {c: conclusions.get(c) for c in OLD_CONTEXTS},
        "new_conclusion": new_conclusion,
        "old_job_timing": old_t,
        "new_job_timing": new_t,
        "verdict": verdict,
        "comparator": "NOT-RUN",
    }
    corpus_path = Path(args.corpus)
    corpus: dict = {"pairs": []}
    if corpus_path.exists():
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    pairs = [p for p in corpus.get("pairs", []) if p.get("id") != pair["id"]]
    pairs.append(pair)
    corpus["pairs"] = sorted(pairs, key=lambda p: p["id"])
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(json.dumps(corpus, indent=2) + "\n", encoding="utf-8")
    print(f"B14 corpus pair {pair['id']} class={args.cls} verdict={verdict} "
          f"old_missing={len(missing_old)} new={new_conclusion}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
