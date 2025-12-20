## B0.5.4.0 — GitHub CI Truth-Layer Evidence (Backend Only)

### Scope
- Backend-only Zero-Drift v3.2 validation in GitHub Actions.
- Frontend untouched.

### Commit / Branch Under Test
- Branch: b0540-zero-drift-v3-proofpack
- CI workflow target commit: _pending CI run_ (align to current branch head on dispatch)

### CI Workflow Entry Points
- `.github/workflows/ci.yml` now contains job `zero-drift-v3-2` (triggered on `workflow_dispatch` and on main/develop).
- Script executed: `scripts/ci/zero_drift_v3_2.sh`.

### Zero-Drift v3.2 CI Gates (CG-1 .. CG-7)
- CG-1 CI run existence: **PENDING** (trigger `ci.yml` via workflow_dispatch or PR to main/develop for this branch).
- CG-2 Fresh DB migration determinism: **PENDING** (asserted by script).
- CG-3 Seed-before-upgrade determinism: **PENDING**.
- CG-4 Matview registry coherence & refresh permissions: **PENDING**.
- CG-5 Beat dispatch proof: **PENDING**.
- CG-6 Serialization enforced in refresh path: **PENDING**.
- CG-7 Worker ingestion write-block: **PENDING**.

### How to Trigger CI (workflow_dispatch)
1) In GitHub UI: Actions → CI → “Run workflow”.
2) Select branch: `b0540-zero-drift-v3-proofpack`.
3) Run workflow. Capture run URL.

### Artifacts to Capture Post-Run
- CI run URL.
- `zero-drift-v3-2` job log anchors proving each CG gate (script outputs include all commands/results).
- Update this file with PASS/FAIL per gate + log links after run completes.

### Notes
- No frontend changes.
- Database/broker use Postgres service; roles/db created inside harness.
