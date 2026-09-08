# Required-Execution Authority Model (Corrective VIII §14)

## Problem

A required check is identified to auditors and to GitHub branch protection by
`(context name, SHA)`. The repository's workflows historically emitted several
required contexts -- including `R6 Worker Resource Governance` -- from three
trigger lifecycles (`pull_request`, `merge_group`, `push` to `main`) under one
name. The exact protected-main SHA `97721048` therefore carried both a
merge-group GREEN and a later push RED for the same required name, with no
machine-readable distinction between them. "80/80 required checks green" is
epistemically meaningless while that ambiguity exists.

## Decision (least-complex architecture)

Separate the lifecycles by trigger elimination; do not rename the governing
contexts (renaming 80 required contexts would require a synchronized
branch-protection change with a far larger blast radius). Gating the job with
`if:` is explicitly NOT accepted: the merge-governance validator correctly
refuses conditional required contexts (a skipped required context is not a
passed one, and the merge queue would wait on it forever).

| Lifecycle | Event | Authority | Required-name emission |
|---|---|---|---|
| MERGE ADMISSION PROOF | `merge_group` | GOVERNING: the only verdict that admits a merge and certifies the landed tree | YES (e.g. `R6 Worker Resource Governance`) |
| PRE-MERGE SIGNAL | `pull_request` | advisory signal on PR bytes; never admission | YES (same name; superseded per-push by concurrency cancel) |
| POST-MERGE SOAK / DIAGNOSTIC | `push` to `main` | NON-GOVERNING soak | NO for R6 -- the workflow has no `push` trigger at all, so a competing post-merge emission of the required name is structurally impossible |

Concretely for R6 (the observed contradictory context):

* The workflow triggers are `workflow_dispatch` + `pull_request` +
  `merge_group` only. There is no `push` trigger and no event `if:` guard on
  the required job (unconditional, as merge governance demands).
* Post-merge soak for the R6 proof is covered by the R7 diagnostic lane
  (non-required), which re-runs the R6 gathering under its own lifecycle.
* The job self-checks this model every run via
  `scripts/ci/validate_b25_p14_viii_execution_identity.py` (falsifier B's
  sensor): re-adding a `push` trigger turns R6 RED.

## What creates / proves a candidate

* What event creates the adjudicated candidate: the merge queue forming a
  merge group (temporary merge of `main` + PR head).
* Which run proves it: the `merge_group` workflow run for that group.
* Unique identification: `(SHA, workflow name, run id, check-run id, event)`.
  Recovery commands (no name-only matching):
  * `gh run list --commit <SHA> --event merge_group`
  * `gh api repos/{owner}/{repo}/commits/<SHA>/check-runs --paginate`
    then filter `check_suite.app.slug == 'github-actions'` and the run's
    `event == 'merge_group'`.
* Can another run with the same name contradict it: NO for R6 after this
  corrective -- push no longer emits the required name, and PR runs are
  superseded by concurrency cancel (`cancel-in-progress` on `pull_request`
  only; `merge_group`/`push` runs never cancel).
* Governing rule on conflict: the `merge_group` conclusion governs. A later
  push soak result (distinct name) is diagnostic and can never override,
  mask, or revoke merge admission.
* Landed-main verification: for single-PR merge groups the merge queue
  guarantees group tree == PR-head tree == landed tree (audited for #722);
  the R6 SHA guard (`git rev-parse HEAD == GITHUB_SHA`) plus the readiness
  evidence binds the proof to the exact bytes. Multi-PR groups would require
  per-PR tree comparison before claiming landed equivalence (known limit).
* Later auditor recovery: SHA-anchored artifacts under
  `docs/forensics/validation/runtime/R6_context_gathering/<SHA>/`
  (`R6_ENV_SNAPSHOT.json` carries `run_url`, `R6_WORKER_READINESS.json`
  carries the observed ready timestamp, `R6_WORKER_LIFECYCLE.json` carries
  parent-PID liveness across the probe sequence).

## Fleet scope and debt

The census at corrective time shows the `pull_request + merge_group + push`
triple-trigger pattern across most required lanes (see report). Corrective
VIII repairs the observed P14 proof plane (R6) and documents the pattern;
applying the same `push`-exclusion to the remaining ~79 required contexts is
explicit forward debt, to be rolled out lane by lane with the same sensor
pattern rather than as an unreviewable flag-day. Until then, auditors MUST
filter check-runs by `event == 'merge_group'` (never by name+SHA alone) when
adjudicating any lane outside the repaired R6 plane.

## Falsification

* Re-add a `push` emission of the required R6 name (remove the `if:` guard):
  `validate_b25_p14_viii_execution_identity.py` exits 1 and the R6 job REDs.
  Exact restore (guard back) returns GREEN. Demonstrated in the VIII report.
* `R6_WORKER_READINESS.json` with `ready != true`, or a missing file: the
  `Verify R6 runtime probes` step REDs (no sleep-through PASS possible).
