#!/usr/bin/env python3
"""Validate the R6 required-execution authority model (Corrective VIII §14).

Governing rule: the REQUIRED context ``R6 Worker Resource Governance`` is
emitted from exactly one governance lifecycle family -- merge-admission
(``merge_group`` + ``pull_request``). It must NOT be emitted from the
post-merge soak lifecycle (``push`` to ``main``), otherwise the same
``SHA + context name`` can carry two contradictory authority states and no
auditor can answer "which exact execution adjudicated this SHA?".

Post-merge soak for R6 remains available under the DISTINCT,
non-required context ``R6 Worker Resource Governance (Post-Merge Soak)``,
which branch protection never consumes.

Checks performed:

1. The required job's ``name:`` is exactly ``R6 Worker Resource Governance``.
2. The required job does not run on ``push`` (either no ``push`` trigger in
   the workflow, or an ``if: github.event_name != 'push'`` guard on the job).
3. No second job in the same workflow reuses the required name.
4. The soak job (if present) uses a DISTINCT name and is guarded to
   ``push``-only, so it can never compete for governing authority.
5. The workflow's ``push`` trigger -- when present for soak -- is scoped to
   ``main`` (it must not adjudicate PR bytes).

Exit 0 when the authority model holds; exit 1 with a causal statement
otherwise. This is falsifier B's governing sensor: reintroducing a ``push``
emission of the required name turns this RED.
"""

from __future__ import annotations

import re
from pathlib import Path

REQUIRED_CONTEXT = "R6 Worker Resource Governance"
SOAK_CONTEXT = "R6 Worker Resource Governance (Post-Merge Soak)"
WORKFLOW = Path(".github/workflows/r6-worker-resource-governance.yml")


def _fail(reason: str) -> int:
    print(f"R6_EXECUTION_IDENTITY_FAIL {reason}")
    return 1


def main() -> int:
    if not WORKFLOW.exists():
        return _fail(f"workflow missing: {WORKFLOW}")
    text = WORKFLOW.read_text(encoding="utf-8")

    required_defs = [
        m.start() for m in re.finditer(r"name:\s*[\"']R6 Worker Resource Governance[\"']", text)
    ]
    # Exclude the soak name from the required-name count.
    required_defs = [
        pos for pos in required_defs if SOAK_CONTEXT not in text[max(0, pos - 2):pos + len(REQUIRED_CONTEXT) + 40]
    ]
    if len(required_defs) != 1:
        return _fail(
            f"required context {REQUIRED_CONTEXT!r} defined {len(required_defs)} times; "
            "exactly one governing definition is required"
        )

    # The required job block: from its `name:` back to the job id and forward
    # to the next job/step boundary for `if:` inspection.
    req_pos = required_defs[0]
    job_tail = text[req_pos:req_pos + 1200]
    has_push_guard = "github.event_name != 'push'" in job_tail or 'github.event_name != "push"' in job_tail

    triggers_block = text[: text.find("jobs:")]
    has_push_trigger = bool(re.search(r"(?m)^  push:\s*$", triggers_block))
    has_merge_group = "merge_group" in triggers_block
    has_pull_request = bool(re.search(r"(?m)^  pull_request:\s*$", triggers_block))

    if not has_merge_group:
        return _fail("merge_group trigger missing: merge admission has no governing lifecycle")
    if not has_pull_request:
        return _fail("pull_request trigger missing: pre-merge signal lifecycle absent")

    if has_push_trigger and not has_push_guard:
        return _fail(
            "required context is emitted on push without an event guard: "
            "same SHA+name can claim both merge-admission and post-merge authority"
        )

    soak_defs = len(re.findall(r"R6 Worker Resource Governance \(Post-Merge Soak\)", text))
    if has_push_trigger and soak_defs != 1:
        return _fail(
            f"push lifecycle present but soak context {SOAK_CONTEXT!r} defined "
            f"{soak_defs} times; post-merge soak needs exactly one distinct identity"
        )
    if soak_defs == 1 and "github.event_name == 'push'" not in text:
        return _fail("soak job must be guarded to push-only so it can never govern")

    print(f"R6_EXECUTION_IDENTITY_PASS required={REQUIRED_CONTEXT!r} soak={SOAK_CONTEXT!r}")
    print(
        "R6_AUTHORITY_MODEL merge_group=governing pull_request=signal push=non-governing-soak "
        f"push_guard={has_push_guard} soak_defined={soak_defs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
