# B0.6 Phase 1 Remediation Evidence Pack

Date: 2026-01-27

## SHAs

- Before: `2fc0a5365ebaeffd5f04c38233f7648624099501`
- After: PENDING

## Context Delta Re-validation

See `docs/forensics/phase1_context_delta_notes.md`.

## Files Changed

- `.env.example`
- `.github/workflows/b06_phase0_adjudication.yml`
- `.github/workflows/ci.yml`
- `backend/app/api/revenue.py`
- `backend/app/core/config.py`
- `backend/app/db/deps.py`
- `backend/app/main.py`
- `backend/app/security/__init__.py`
- `backend/app/security/auth.py`
- `backend/requirements.txt`
- `tests/test_b06_realtime_revenue_v1.py`
- `tests/test_b060_phase1_auth_tenant.py`
- `docs/forensics/phase1_context_delta_notes.md`
- `docs/forensics/b060_phase1_remediation_evidence.md`

## Commands Executed

- `git status -sb`
- `git rev-parse HEAD`
- `rg -n "Authorization|B0_6_BEARER_TOKEN|Bearer" backend -g "*.py"`
- `rg -n "jwt|JWT|jose|jwks|pyjwt|oauth2|OAuth2" backend -g "*.py"`
- `rg -n "auth_context|request.state" backend/app -g "*.py"`
- `Get-Content backend/app/core/tenant_context.py`
- `Get-Content backend/app/db/session.py`
- `Get-Content backend/app/main.py`
- `Get-Content .github/workflows/b06_phase0_adjudication.yml`
- `Get-Content .github/workflows/ci.yml | Select-String -Pattern "test_b06_realtime_revenue_v1" -Context 3,3`
- `Get-Content tests/test_b06_realtime_revenue_v1.py`

## CI Run Link

PENDING (run CI after merge).

## CI Log Excerpt (Gate P1-F)

PENDING (capture once CI run completes).
