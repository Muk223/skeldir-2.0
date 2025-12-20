## B0.5.4.0 — GitHub CI Truth-Layer Evidence (Backend Only)

### Scope
- Backend-only Zero-Drift v3.2 validation in GitHub Actions.
- Frontend untouched.

### Commit / Branch Under Test
- Branch: b0540-zero-drift-v3-proofpack
- CI workflow target commit: 53f65ac03023de816fb6e3bd03836cecc0e67825 (branch head at dispatch)
- CI workflow run: https://github.com/Muk223/skeldir-2.0/actions/runs/20399899759 (workflow_dispatch)

### CI Workflow Entry Points
- `.github/workflows/ci.yml` now contains job `zero-drift-v3-2` (triggered on `workflow_dispatch` and on main/develop).
- Script executed: `scripts/ci/zero_drift_v3_2.sh`.

### Zero-Drift v3.2 CI Gates (CG-1 .. CG-7)
- CG-1 CI run existence: **PASS** - workflow_dispatch run 20399899759 executed on `b0540-zero-drift-v3-proofpack` (Zero-Drift v3.2 job invoked).
- CG-2 Fresh DB migration determinism: **PASS** - ZG-1 fresh upgrade reached head on `skeldir_zg_fresh` (Alembic log stack starting at `== ZG-1: fresh DB upgrade to head ==` in Zero-Drift job log).
- CG-3 Seed-before-upgrade determinism: **PASS** - ZG-2 seeded `skeldir_zg_existing`, upgraded to head, and selected seeded attribution_event row (log block after `== ZG-2: existing DB seed-before-upgrade ==` showing INSERTs and final SELECT).
- CG-4 Matview registry coherence & refresh permissions: **PASS** - ZG-3/4 enumerated mv_* registry, owners `app_user`, unique indexes present, and REFRESH MATERIALIZED VIEW succeeded for fresh + existing contexts.
- CG-5 Beat dispatch proof: **PASS** - ZG-5 emitted beat_schedule JSON (`beat_schedule_loaded: true`, 3 tasks) and Celery beat startup log in Zero-Drift job.
- CG-6 Serialization enforced in refresh path: **FAIL** - ZG-6 aborted with `ImportError: cannot import name 'BEAT_SCHEDULE' from partially initialized module 'app.tasks.maintenance' (circular import)` before lock/refresh proof.
- CG-7 Worker ingestion write-block: **FAIL** - ZG-7 not executed because harness stopped at ZG-6; worker-context INSERT block evidence absent.

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
