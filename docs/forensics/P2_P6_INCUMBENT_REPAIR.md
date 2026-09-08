# Phase II — Pre-Promotion Incumbent P6 Repair (Directive-2 §0.6)

**State:** PRE-PROMOTION repair. Incumbent authority preserved; no successor
authority added; no context renamed; no cutover performed.
**Branch:** `p2-p6-incumbent-repair` from `origin/main@12db0403`.
**Landed:** PR #723 → `main@0d513130` via `main-merge-queue` ALLGREEN
2026-09-08T02:39:41Z. Live proof: CI run 34160397839,
`b14-p6-runtime-artifacts` contains `junit.enforcer.xml` (4 tests,
0 failures), `proof_plane_report.json`, `tests.log`.
**Scope:** `b14-p6-proof-plane-binding` (vacuity repair) + `set -o pipefail`
on the sibling B1.4 `| tee` pytest steps (same failure-masking defect class).

## 1. Vacuity finding (ACCEPTED from Agent-2, narrowly confirmed)

Causal chain, each link evidenced:

1. `backend/tests/conftest.py` Gate C: when `CI=true` and `DATABASE_URL` is
   absent, pytest aborts at import with `RuntimeError: [B0.5.3.3 Gate C]`.
   GitHub Actions sets `CI=true` by default on every runner.
2. Incumbent `b14-p6-proof-plane-binding` set no `DATABASE_URL` and ran no
   Postgres service (verified in `ci.yml` pre-repair: job env held only
   `PYTHONPATH`; all seven sibling B1.4 jobs set `DATABASE_URL` + service).
3. Local reproduction: `CI=true` without `DATABASE_URL` →
   `pytest backend/tests/test_b14_p6_proof_plane_binding_enforcer.py` exits
   **4** (conftest `RuntimeError`), no junit file written.
4. The step piped pytest through `| tee artifacts/b14_p6/tests.log` with no
   `set -o pipefail`. Pipeline exit status is then tee's (0), so the step —
   and the job — reported GREEN.
5. `mkdir -p artifacts/b14_p6` + the enforcer `--report-json` + tee's
   `tests.log` guaranteed the upload path was non-empty, so
   `if-no-files-found: error` could not fire.
6. Live corroboration: same-SHA pair `5da45dbc` (CI run 34141912982 SUCCESS /
   shadow 34141912972 SUCCESS) — the comparator verdict is
   `RED:missing-old-proof:p6/junit.enforcer.xml`. The required context was
   green while its proof artifact did not exist.

Verdict: **P6 was vacuous since introduction** (present at least since the
Phase I baseline). Its suite is static (subprocess checks, no DB I/O), so no
proof semantics change by providing a database; Gate C only demands a
localhost DSN be present.

## 2. Repair (identity-preserving)

`b14-p6-proof-plane-binding` only:

- Added the standard Postgres service block (byte-identical to siblings).
- Added job env `DATABASE_URL` / `MIGRATION_DATABASE_URL` (same localhost
  values as every sibling B1.4 job) + `TESTING: "1"`.
- Added `set -o pipefail` to the `Run B1.4-P6 enforcer tests` step so a
  pytest failure propagates through `tee`.
- Context name unchanged
  (`B1.4 P6 Merge-Blocking Privacy Proof Plane Binding`); `needs:` edges
  unchanged; no successor context added; contract untouched (v1.21.0, 80/80).

Ancillary (same defect class, same slice): `set -o pipefail` on the B1.4
p0 (2 steps), p5, and p7 pytest `| tee` steps. Those proofs execute (DB
present) but a failure would likewise be masked. Strictly stronger proof;
no threshold, command, or topology change.

## 3. Controls

- Positive: `pytest backend/tests/test_b14_p6_proof_plane_binding_enforcer.py`
  with a localhost `DATABASE_URL` → 4 passed, junit written (run locally).
- Negative (enforcer): `--simulate-regression` → non-zero, expected message
  (unchanged step, still enforced in CI).
- Negative (propagation): pre-repair step text had `| tee` with no pipefail
  (static fact); post-repair step text carries `set -o pipefail` (static
  fact). Live proof arrives with the repair PR's own CI run: the P6 job must
  be green **with** `b14-p6-runtime-artifacts` containing
  `junit.enforcer.xml` (4 tests), `proof_plane_report.json`, `tests.log`.
- Guard: `validate_ci_physics.py` + 24/24 negative controls re-run on the
  repair branch before opening the PR.

## 4. Corpus consequence (Directive-2 §0.7)

The two existing pairs (`5da45dbc`, `ffc37f5b`) remain
**DIAGNOSTIC PRE-REPAIR EVIDENCE** (comparator RED, p6 artifact absent).
After this repair lands and the shadow branch re-bases onto the repaired
main, the qualifying promotion corpus resets to **0/10**; no RED pair counts
toward promotion.

## 5. Pre-promotion compliance (§0.6)

- [x] proof executes (DB env + service provided)
- [x] proof failure propagates (pipefail)
- [x] expected artifact exists on success (junit; upload errors if absent)
- [x] incumbent B1.4 authority not retired (all 8 contexts still required)
- [x] no successor authority added (shadow still non-required, not in contract)
- [x] current context not renamed
- [x] no cutover performed
