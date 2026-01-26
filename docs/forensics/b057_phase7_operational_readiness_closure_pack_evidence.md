# B0.5.7 Phase 7 - Operational Readiness Closure Pack Evidence

Status: DRAFT (requires CI run on this commit for final anchoring)
Collected: 2026-01-25T19:56:22.2733383-06:00

## A) P6 Drift Check (INDEX vs CI run)

Command:
```powershell
rg -n "B0\.5\.7 Phase 6" docs/forensics/INDEX.md
```
Output:
```text
38:| B0.5.7 Phase 6 | docs/forensics/b057_phase6_ci_enforcement_governance_cleanup_evidence.md | CI enforcement + governance cleanup (least-privilege E2E, Postgres-only guardrails, INDEX enforcement) | 0a470df0f7b7d480ded10060cd4457955284e8ad | https://github.com/Muk223/skeldir-2.0/actions/runs/21340267507 |
```

Command:
```powershell
$ProgressPreference='SilentlyContinue'; Invoke-RestMethod -Uri "https://api.github.com/repos/Muk223/skeldir-2.0/actions/runs/21340267507" -Headers @{"Accept"="application/vnd.github+json"} | Select-Object head_sha, html_url, status, conclusion, created_at, updated_at | ConvertTo-Json -Depth 3
```
Output:
```json
{
    "head_sha":  "0a470df0f7b7d480ded10060cd4457955284e8ad",
    "html_url":  "https://github.com/Muk223/skeldir-2.0/actions/runs/21340267507",
    "status":  "completed",
    "conclusion":  "success",
    "created_at":  "2026-01-25T21:59:26Z",
    "updated_at":  "2026-01-25T22:05:44Z"
}
```

Result: INDEX Phase 6 commit SHA matches CI run head_sha. H-P7-1 falsified.

## B) Non-optional enforcement (required checks)

Attempted to query branch protection (requires authentication):
```powershell
$ProgressPreference='SilentlyContinue'; try { Invoke-RestMethod -Uri "https://api.github.com/repos/Muk223/skeldir-2.0/branches/main/protection" -Headers @{"Accept"="application/vnd.github+json"} | ConvertTo-Json -Depth 2 } catch { $_.Exception.Message; if ($_.ErrorDetails) { $_.ErrorDetails.Message } }
```
Output:
```text
The remote server returned an error: (401) Unauthorized.
{
  "message": "Requires authentication",
  "documentation_url": "https://docs.github.com/rest",
  "status": "401"
}
```

Conclusion: Required checks configuration cannot be verified in-code. Manual verification is required in GitHub settings.

## C) Evidence pack inventory (B0.5.7)

Command:
```powershell
Get-ChildItem docs/forensics -Filter "b057_*" | Select-Object Name
```
Output:
```text
Name
----
b057_context_gathering_inventory_evidence.md
b057_phase3_webhook_ingestion_unblocking_evidence.md
b057_phase4_llm_audit_persistence_evidence.md
b057_phase5_full_chain_e2e_integration_evidence.md
b057_phase6_ci_enforcement_governance_cleanup_evidence.md
```

## D) Governance enforcement durability (INDEX SHA consistency)

Change implemented in `scripts/ci/enforce_forensics_index.py`:
- New check enforces that any changed B0.5.7 INDEX row has commit SHA equal to CI `ADJUDICATED_SHA`/`GITHUB_SHA`.
- Scope limited to changed rows in `docs/forensics/INDEX.md` and to B0.5.7 rows only.

Negative test (descriptive):
- If a PR changes a B0.5.7 INDEX row with commit SHA != `GITHUB_SHA`, CI fails with:
  `INDEX commit SHA mismatch for B0.5.7 row: expected <sha>, got <sha>`.

## E) Closure pack artifact

File created:
- `docs/forensics/root/B057_OPERATIONAL_READINESS_CLOSURE_PACK.md`

This document includes the required sections and an evidence anchor table.

## F) Working tree status (pre-commit)

Command:
```powershell
git status --porcelain=v1
```
Output:
```text
 M scripts/ci/enforce_forensics_index.py
?? docs/forensics/root/B057_OPERATIONAL_READINESS_CLOSURE_PACK.md
```

## G) INDEX Phase 7 row (query-based CI anchor)

Phase 7 row added with commit SHA and a query-based CI workflow URL (resolves to the run for this SHA once CI completes):
```
| B0.5.7 Phase 7 | docs/forensics/b057_phase7_operational_readiness_closure_pack_evidence.md | Operational readiness closure pack + governance durability proof | 72cc598b1bf55670a0b6aa67287d3d1ce02c508f | https://github.com/Muk223/skeldir-2.0/actions/workflows/ci.yml?query=branch:main+event:push+sha:72cc598b1bf55670a0b6aa67287d3d1ce02c508f |
```

## H) Next required anchors (blocking)

- CI run on commit 72cc598b1bf55670a0b6aa67287d3d1ce02c508f must complete; replace the query URL with the concrete run URL after completion.
