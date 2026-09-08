#!/usr/bin/env python3
"""Validate the R6 required-execution authority model (Corrective VIII §14).

Governing rule: the REQUIRED context ``R6 Worker Resource Governance`` is
emitted from exactly one governance lifecycle family -- merge-admission
(``merge_group`` + ``pull_request``). The workflow must have NO ``push``
trigger: a push emission under the same required name once let one SHA carry
both a merge-group GREEN and a later push RED with no machine-readable
distinction between them.

Two structural properties are enforced (falsifier B's governing sensor):

1. No ``push`` trigger exists in the R6 workflow, so a competing
   post-merge emission of the required name is structurally impossible
   (``eliminating duplicate trigger paths``, §14). Re-adding ``push``
   turns this RED.
2. The required job is unconditional (no event ``if:`` guard): the
   merge-governance validator correctly refuses skipped required contexts,
   so gating is not an accepted substitute for trigger elimination.

Auditor recovery for the governing run (never name+SHA alone):

    gh run list --commit <SHA> --event merge_group

Exit 0 when the authority model holds; exit 1 with a causal statement
otherwise.
"""

from __future__ import annotations

import re
from pathlib import Path

REQUIRED_CONTEXT = "R6 Worker Resource Governance"
WORKFLOW = Path(".github/workflows/r6-worker-resource-governance.yml")


def _fail(reason: str) -> int:
    print(f"R6_EXECUTION_IDENTITY_FAIL {reason}")
    return 1


def main() -> int:
    if not WORKFLOW.exists():
        return _fail(f"workflow missing: {WORKFLOW}")
    text = WORKFLOW.read_text(encoding="utf-8")

    required_defs = len(
        re.findall(r"name:\s*[\"']R6 Worker Resource Governance[\"']", text)
    )
    if required_defs != 1:
        return _fail(
            f"required context {REQUIRED_CONTEXT!r} defined {required_defs} times; "
            "exactly one governing definition is required"
        )

    triggers_block = text[: text.find("jobs:")]
    has_push_trigger = bool(re.search(r"(?m)^  push:\s*$", triggers_block))
    if has_push_trigger:
        return _fail(
            "push trigger present: the same required name could again claim both "
            "merge-admission and post-merge authority for one SHA"
        )
    if "merge_group" not in triggers_block:
        return _fail("merge_group trigger missing: merge admission has no governing lifecycle")
    if not re.search(r"(?m)^  pull_request:\s*$", triggers_block):
        return _fail("pull_request trigger missing: pre-merge signal lifecycle absent")

    req_pos = text.find(f'name: "{REQUIRED_CONTEXT}"')
    job_tail = text[req_pos:req_pos + 800]
    if "github.event_name" in job_tail:
        return _fail(
            "required job carries an event guard: a skipped required context is not "
            "a passed one; eliminate the duplicate trigger path instead of gating"
        )

    print(f"R6_EXECUTION_IDENTITY_PASS required={REQUIRED_CONTEXT!r}")
    print("R6_AUTHORITY_MODEL merge_group=governing pull_request=signal push=eliminated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
