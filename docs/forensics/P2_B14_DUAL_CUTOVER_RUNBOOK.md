# Phase II Slice 1 — DUAL/CUTOVER Runbook (OWNER-GATED, NOT EXECUTED)

No step below has been executed. Each step requires explicit owner approval
and a green predecessor. The migration gate (`validate_b14_migration.py`)
refuses every unlawful intermediate state; run it before AND after each step.

## Preconditions (all must hold)

1. Equivalence corpus GREEN: `docs/forensics/p2_b14_equivalence_corpus.json`
   with >=10 pairs (>=3 high_risk, >=2 docs_only, >=2 merge_group, >=1
   red_team), all same-SHA, comparator GREEN on each, red-team demonstrates
   FailureClass_old == FailureClass_new.
2. P2-C7: incumbent queue p50 during shadow within 20% of matched baseline.
3. Live-control-plane audit: check-run SHAs, branch protection, merge queue
   inspected live (offline clone cannot do this).
4. No in-flight PR can be stranded: every open PR receives the new context
   naturally (new workflow fires on pull_request unfiltered); verified by
   listing open PRs and their check suites.

## Step 1 — DUAL (add NEW required, keep OLD required)

Files (one PR, through merge queue, no bypass):
- `contracts-internal/governance/b03_phase2_required_status_checks.main.json`:
  v1.21.0 -> v1.22.0-dual, ADD `B1.4 Privacy Consolidated Plane` (keep all 80).
- `ci.yml` job `b14-p6-proof-plane-binding`: ADD `DATABASE_URL` +
  `MIGRATION_DATABASE_URL` env (same localhost values as sibling B14 jobs).
  Rationale: conftest B0.5.3.3 Gate C crashes the p6 pytest at import without
  it (masked by `| tee`, job green-vacuous since PR #713; evidence 816-byte
  artifact). This makes the existing suite execute; no test, threshold, or
  topology change. Required so DUAL pairs are junit-to-junit comparable
  (pair #1 comparator RED is otherwise uncloseable).
- `contracts-internal/governance/ci_proof_conservation.v1.json`: v1.0.2 ->
  v1.0.3, add I-1 successor mapping (8 predecessors -> new context) + corpus ref.
- `.github/workflows/b14-privacy-consolidated.yml`: remove the two
  `physics-exempt` lines (lane is now required; exemptions lapse), keep all
  triggers.
- Forensics: corpus + this runbook execution record, INDEX rows.

Admin (owner only, after the above lands + one green DUAL entry observed):
- Add `B1.4 Privacy Consolidated Plane` to `main` branch protection required
  contexts (now 81). Verify: `gh api .../protection/required_status_checks`
  shows 81 == contract v1.22.0-dual (set-difference empty both directions).

Gate: `python scripts/ci/validate_b14_migration.py` -> GREEN state=DUAL.
Live verify: one PR + one merge_group entry show 81/81 terminal incl. both
old B14 (8x) and new consolidated (1x) on the SAME SHA.

## Step 2 — observation

At least 3 merge-group entries + 5 PRs fully green in DUAL (both lanes agree;
any divergence halts promotion and reopens the corpus).

## Step 3 — CUTOVER (retire OLD authority, delete OLD implementation)

Files (one PR, through merge queue):
- Contract v1.22.0-dual -> v1.23.0: REMOVE the 8 old B14 contexts (73+1=74?
  recompute: 81-8=73... verify count at execution time, never assert).
- `ci.yml`: DELETE jobs b14-p0..b14-p7 (8 jobs) and their artifact uploads.
  Nothing else in ci.yml changes (needs: edges of other jobs untouched;
  b14-p6/p7 were terminals, so no downstream rewiring).
- Matrix v1.0.4: mark predecessors retired, successor authoritative.

Admin (owner only, after landing + one green CUTOVER entry):
- Remove the 8 old B14 contexts from branch protection. Verify 73 == contract.

Gate: `validate_b14_migration.py --corpus <corpus>` -> GREEN state=CUTOVER.
Falsifier re-run: premature-removal synthetic tree must still RED.

## Step 4 — post-cutover

- Re-measure: cohort construction counts from runtime logs, queue p50/p90,
  wall p50 (report vs pre-slice baseline; feed C2-07/08/09/10 evidence).
- Close or re-scope PR #721 (shadow vehicle).
- Open slice 2 (B13, same machine).

## Rollback

- DUAL rollback: remove NEW from protection + revert contract (OLD never
  left; no PR stranding: new context simply stops being required).
- CUTOVER rollback: re-add OLD contexts + revert ci.yml deletion (one revert
  PR through the queue). Shadow workflow retained until rollback window closes.

## Forbidden (automatic fail)

Mass rebase, close/reopen, admin bypass, protection relaxation, freeze,
`delete-then-hope` (OLD removed before NEW live+equivalent).
