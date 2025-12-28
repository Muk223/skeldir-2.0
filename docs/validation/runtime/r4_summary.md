# R4 Worker Failure Semantics Summary (Truth Anchor)

## Status

R4 = **IN PROGRESS**.

- **Candidate SHA:** `TBD` (must be a single CI run proving all gates)
- **CI run:** TBD (browser-visible logs are the authority)
- **Last updated:** `2025-12-28`

## Current Blocking Gates (per latest adjudication)

- **EG-R4-FIX-1 (Postgres-only fabric is browser-provable):** Requires CI logs to show `R4_BROKER_SCHEME=sqla+postgresql`, `R4_BACKEND_SCHEME=db+postgresql`, plus `R4_*_DSN_SHA256` hashes (schemes must hard-fail otherwise).
- **EG-R4-FIX-2 (Explicit cross-tenant RLS bypass attempt):** Requires CI logs to show tenant A attempting to read a tenant B row by primary key (`R4_S3_TENANT_A=... R4_S3_TENANT_B=... R4_S3_TARGET_ROW_ID=...`) and returning `R4_S3_RESULT_ROWS=0` (or explicit deny). Any `>0` must hard-fail the run.

## Evidence Policy

No artifact-only proofs. If the proof is not visible in the GitHub Actions run logs, it is inadmissible.

## Next Required Action

Run the updated `.github/workflows/r4-worker-failure-semantics.yml` on a single commit SHA and update this file with that run URL + SHA only after all gates pass in browser-visible logs.

