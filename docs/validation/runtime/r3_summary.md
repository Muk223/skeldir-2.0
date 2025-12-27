# R3 Ingestion Under Fire Validation Summary (Truth Anchor)

## Status

R3 = **IN PROGRESS** until one CI run proves all exit gates in logs.

- **Candidate SHA:** `TBD`
- **CI run:** `TBD` (paste GitHub Actions run URL)

## Mission (Non-Negotiable)

Adversarially stress the live ingestion pipeline end-to-end (HTTP → API → validation/sanitization → DB insert or DLQ) and prove, in CI logs alone:

- **Idempotency under replay storms** is race-safe and client-stable (no 5xx).
- **Malformed storms** route deterministically to DLQ without crashes/5xx.
- **Idempotency is tenant-correct** (no cross-tenant collisions).
- **PII cannot persist** in canonical or DLQ payload surfaces.

## Exit Gates (Pass Matrix)

| Gate | Description | Status |
|------|-------------|--------|
| EG-R3-0 | Truth anchor & clean room (candidate SHA + deterministic tenants) | TBD |
| EG-R3-1 | Idempotency under fire (ReplayStorm) | TBD |
| EG-R3-2 | Tenant-correct idempotency (CrossTenantCollision) | TBD |
| EG-R3-3 | DLQ reliability (MalformedStorm) | TBD |
| EG-R3-4 | PII self-defense (PIIStorm) | TBD |
| EG-R3-5 | MixedStorm stability | TBD |
| EG-R3-6 | Evidence pack is browser-verifiable (verdict blocks + DB truth) | TBD |

## Evidence (Where It Lives)

- Workflow: `.github/workflows/r3-ingestion-under-fire.yml`
- Harness: `scripts/r3/ingestion_under_fire.py`

