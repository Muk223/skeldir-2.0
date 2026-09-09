#!/usr/bin/env python3
"""Attest the exact-SHA independent B2.5 C19/C20/C21 preservation proof."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SOURCE_CONTEXT = "B2.5-P13 E2E Trust Closure"
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
SOURCE_WORKFLOW_PATH = ".github/workflows/b2_5-p13-e2e-trust-closure.yml"
REQUIRED_JOBS = (
    "B2.5-P13 C19 Context-Robust Production Closure",
    "B2.5-P13 C20 Verdict Authority Conservation",
    "B2.5-P13 C21 Freshness and Issuance Authority Conservation",
    "B2.5-P14 Downstream Projection Safety",
)


class AttestationError(RuntimeError):
    """The exact candidate lacks a successful independent inherited proof."""


def _get(url: str, token: str) -> Any:
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AttestationError(f"github_query_failed:{exc}") from exc


def _all_check_runs(*, repository: str, sha: str, token: str) -> list[dict[str, Any]]:
    """Return every check run for the candidate, not only GitHub's first page."""
    checks: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = _get(
            f"https://api.github.com/repos/{repository}/commits/{sha}/check-runs"
            f"?per_page=100&page={page}",
            token,
        )
        batch = payload.get("check_runs", [])
        if not isinstance(batch, list):
            raise AttestationError("github_check_runs_shape_invalid")
        checks.extend(batch)
        if len(batch) < 100:
            return checks
        page += 1


def _source_run(
    *, repository: str, sha: str, event: str, token: str, wait_seconds: int, poll_seconds: int
) -> tuple[dict[str, Any], dict[str, str]]:
    deadline = time.monotonic() + wait_seconds
    last = "source_context_missing"
    while True:
        checks = _all_check_runs(repository=repository, sha=sha, token=token)
        candidates = [check for check in checks if check.get("name") == SOURCE_CONTEXT]
        for check in candidates:
            details_url = str(check.get("details_url", ""))
            marker = "/actions/runs/"
            if marker not in details_url:
                continue
            run_id = details_url.split(marker, 1)[1].split("/", 1)[0]
            run = _get(
                f"https://api.github.com/repos/{repository}/actions/runs/{run_id}", token
            )
            if run.get("head_sha") != sha or run.get("event") != event:
                continue
            if not str(run.get("path", "")).startswith(SOURCE_WORKFLOW_PATH):
                continue
            if check.get("status") != "completed" or check.get("conclusion") != "success":
                last = (
                    f"source_context_not_success:status={check.get('status')}:"
                    f"conclusion={check.get('conclusion')}"
                )
                continue
            jobs_payload = _get(
                f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100",
                token,
            )
            jobs = {str(job.get("name")): str(job.get("conclusion")) for job in jobs_payload.get("jobs", [])}
            required = {name: jobs.get(name, "missing") for name in REQUIRED_JOBS}
            if any(result != "success" for result in required.values()):
                last = f"source_subordinate_not_success:{required}"
                continue
            return run, required
        if time.monotonic() >= deadline:
            raise AttestationError(last)
        print(f"B26_P1_INHERITED_WAIT {last}", flush=True)
        time.sleep(poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--sha", default=os.environ.get("B26_CANDIDATE_SHA"))
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME"))
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN"))
    parser.add_argument("--wait-seconds", type=int, default=2400)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--evidence-out", required=True, type=Path)
    args = parser.parse_args()
    if not all((args.repository, args.sha, args.event, args.token)):
        print("B26_P1_INHERITED_ATTESTATION_FAIL missing_required_argument")
        return 1
    try:
        run, required = _source_run(
            repository=args.repository,
            sha=args.sha,
            event=args.event,
            token=args.token,
            wait_seconds=args.wait_seconds,
            poll_seconds=args.poll_seconds,
        )
    except AttestationError as exc:
        print(f"B26_P1_INHERITED_ATTESTATION_FAIL {exc}")
        return 1
    details = {
        "source_context": SOURCE_CONTEXT,
        "source_workflow": SOURCE_WORKFLOW_PATH,
        "source_run_id": str(run["id"]),
        "source_run_url": run["html_url"],
        "source_event": run["event"],
        "source_sha": run["head_sha"],
        "required_jobs": required,
    }
    from scripts.ci.b26_p1_evidence import write_evidence_cell  # noqa: PLC0415

    write_evidence_cell(
        args.evidence_out,
        gate_id="B26-P1-G1-G2-INHERITED-PHYSICS",
        producer="b26-p1-inherited-conduction",
        scenario_id="b25-p13-context-robust-production-closure",
        falsifier_id="inherited-C19-C20-C21-negative-controls",
        details=details,
    )
    print("B26_P1_INHERITED_ATTESTATION_PASS")
    print(json.dumps(details, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
