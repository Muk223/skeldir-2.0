# B0.6 Phase 3 Remediation Evidence

Date: 2026-01-28
Repo: C:\Users\ayewhy\II SKELDIR II

## SHAs
- Before: 09048cb1af81886c7138cf898ed0f4d765756fb6
- After: 60f4f6e2228c62998735801da1421e76683e8af0 (merge commit for PR #33)

## Migration
- ID: 202601281230
- File: alembic/versions/007_skeldir_foundation/202601281230_b060_phase3_realtime_revenue_cache.py
- Table: revenue_cache_entries (tenant_id + cache_key PK, jsonb payload, data_as_of, expires_at, error cooldown fields)
- RLS: ENABLE + FORCE; tenant_isolation_policy using app.current_tenant_id
- Grants: app_rw/app_ro + app_user

## Cache + Singleflight Substrate
- Service: backend/app/services/realtime_revenue_cache.py
- Locking: pg_try_advisory_xact_lock with deterministic 64-bit key (tenant_id + cache_key)
- Follower behavior: poll until cache fresh or timeout
- Failure cooldown: error_cooldown_until + Retry-After on 503

## Endpoint Integration
- Attribution: backend/app/api/attribution.py (uses shared cache service; ETag + Cache-Control; 503 + Retry-After)
- Canonical v1: backend/app/api/revenue.py (uses same shared cache service; Cache-Control; 503 + Retry-After)

## Tests (Phase 3)
- backend/tests/test_b060_phase3_realtime_revenue_cache.py
  - cache hit avoids upstream call
  - stampede prevention 10?1
  - cross-tenant isolation
  - failure cooldown 503 + Retry-After

## CI Wiring (merge-blocking)
- Phase gate: scripts/phase_gates/b0_6_gate.py
- Manifest: docs/phases/phase_manifest.yaml (B0.6 added to matrix)
- CI workflow: .github/workflows/ci.yml (phase-gates matrix executes run_phase.py across manifest phases)

## Commands (local)
```
# Migrations
alembic upgrade skeldir_foundation@head

# Phase 3 tests
python -m pytest backend/tests/test_b060_phase3_realtime_revenue_cache.py -v
```

## Actions Evidence
- Run URL (CI, required checks): https://github.com/Muk223/skeldir-2.0/actions/runs/21452308598
- Run URL (Contract Artifacts CI): https://github.com/Muk223/skeldir-2.0/actions/runs/21452308636
- Logs (CI run 21452308598):
  - Validate Migrations: success (job 61784100181)
  - Phase Gates (B0.6): success (job 61784132283)
  - Test Backend: success (job 61784100108)
  - Validate Contracts: success (job 61784100107)
  - Governance Guardrails: success (job 61784100125)
- Logs (Contract Artifacts run 21452308636):
  - Contract Integrity Tests (Mocks vs Contracts): success (job 61784130804)
  - Provider Contract Tests (Implementation vs Contracts): success (job 61784130827)

## Docs Updated
- docs/forensics/b06_realtime_revenue_context_pack.md
- docs/forensics/b060_phase3_context_delta_notes.md
- docs/forensics/INDEX.md
