# Phase 1 Context Delta Notes (Re-validation)

Date: 2026-01-27

Objective: Re-verify Phase 1 blockers and CI topology on current `main` HEAD before remediation.

## Step A — Repo state (current truth)

Commands run:
```
git status -sb
git rev-parse HEAD
```

Outputs:
- Branch: `main`, clean working tree.
- HEAD SHA: `2fc0a5365ebaeffd5f04c38233f7648624099501` (same as snapshot).

## Step B — Auth surface (Authorization header + env token checks, JWT utilities)

Commands run:
```
rg -n "Authorization|B0_6_BEARER_TOKEN|Bearer" backend -g "*.py"
rg -n "jwt|JWT|jose|jwks|pyjwt|oauth2|OAuth2" backend -g "*.py"
```

Evidence (paths + notes):
- `backend/app/api/revenue.py`:
  - Handler signature reads `Authorization` header.
  - `_has_bearer_token()` compares token against `B0_6_BEARER_TOKEN` env (default `test-token`).
  - No JWT parsing/verification.
- `backend/app/api/attribution.py`:
  - Handler checks `Authorization` header with `_has_bearer_token()` (string-prefix only).
  - Comment explicitly notes “no JWT verification in B0.1”.
- `backend/app/api/auth.py`:
  - Stub login/refresh return sample JWT strings; no validation utilities.
- No JWT/JWKS libraries or utilities found in backend code beyond schema comments and tenant_context docstrings.

Conclusion:
- BH1 (auth is still stub; no JWT verification) remains true.
- RH1 (contract-first security without runtime enforcement) remains true.

## Step C — Tenant context plumbing and request-state expectations

Commands run:
```
rg -n "auth_context|request.state" backend/app -g "*.py"
Get-Content backend/app/core/tenant_context.py
Get-Content backend/app/db/session.py
Get-Content backend/app/main.py
```

Evidence:
- `backend/app/core/tenant_context.py`:
  - Derivation expects `request.state.auth_context.tenant_id`.
  - Middleware expects `request.state.db_session` to exist.
  - Not registered in `backend/app/main.py`.
- `backend/app/db/session.py`:
  - `get_session(tenant_id)` sets `app.current_tenant_id` via `set_config(...)`.
  - RLS plumbing exists.
- `backend/app/main.py`:
  - Only `PIIStrippingMiddleware` and `ObservabilityMiddleware` are registered.
  - No tenant context middleware wired.

Conclusion:
- BH2 (tenant derived from env fallback) remains true in revenue endpoint.
- BH3 (tenant context middleware exists but not wired) remains true.
- BH4 (RLS session exists but unused by revenue endpoint) remains true.
- RH2/RH3 (pipeline exists but unused; RLS plumbing isolated) remain true.

## Step D — CI test execution topology (B0.6 adjudication)

Commands run:
```
Get-Content .github/workflows/b06_phase0_adjudication.yml
Get-Content .github/workflows/ci.yml | Select-String -Pattern "test_b06_realtime_revenue_v1" -Context 3,3
Get-Content tests/test_b06_realtime_revenue_v1.py
```

Evidence:
- `b06_phase0_adjudication.yml` runs only:
  - `pytest -q tests/test_b06_realtime_revenue_v1.py`
  - `pytest -q tests/contract/test_contract_semantics.py`
- `ci.yml` includes:
  - `pytest ../tests/test_b06_realtime_revenue_v1.py -v --tb=short`
  - `pytest ../tests/contract/test_contract_semantics.py -v --tb=short`
- `tests/test_b06_realtime_revenue_v1.py`:
  - Uses `Authorization: Bearer test-token` (env stub).
  - Only asserts 401 on missing auth and response shape on stub token.

Conclusion:
- BH5 (tests do not prove Phase 1 identity invariants) remains true.
- RH4 (CI selection narrow; identity regressions masked) remains true.

## Summary (validated blockers)

- Auth is stubbed and env-driven, not JWT-validated.
- Tenant identity is env fallback, not claim-derived.
- Tenant context middleware exists but is not wired.
- RLS-aware DB session exists but revenue endpoint does not use it.
- CI runs only Phase 0 tests; no Phase 1 identity tests executed.

