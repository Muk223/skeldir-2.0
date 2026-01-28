# Phase 2 Context Delta Notes (B0.6)

Date: 2026-01-28
Repo: C:\Users\ayewhy\II SKELDIR II

## Step A — Repo truth

Commands:
- git rev-parse HEAD
- git rev-parse --abbrev-ref HEAD
- git rev-parse origin/main
- git log --oneline -n 5 origin/main
- gh api repos/Muk223/skeldir-2.0/branches/main/protection

Findings:
- Current working branch: b060-phase1-evidence-update
- Current HEAD: ed1d62841aa534eb9194c5caeb4355b1c580ca3c
- origin/main: d95d0fbdb4fb8131869bc735adf243b99df73ec1
- origin/main history indicates Phase 1 merge: "Merge pull request #29 from Muk223/b060-phase1-auth-tenant" (commit d95d0fb).
- Branch protection (main) required status checks:
  - "B0.6 Phase 0 Adjudication" only (strict = true). Enforce admins = true. No other required checks listed.

Conclusion:
- Phase 1 auth/tenant work appears merged into main via PR #29.
- Required checks currently only gate B0.6 Phase 0 adjudication; no Phase 2-specific checks exist.

## Step B — Search for existing platform integration substrate

Commands:
- rg -n --glob 'backend/app/**' "oauth|refresh_token|access_token|jwks|client_id|client_secret|ad_account|customer_id|platform_account|google|meta|facebook|ads|stripe|paypal"
- rg -n "stripe_webhook_secret|paypal_webhook_secret" backend

Findings (non-exhaustive, relevant hits):
- Webhook signature verification and per-tenant secrets:
  - backend/app/api/webhooks.py (Stripe/PayPal webhook handlers and signature verification)
  - backend/app/webhooks/signatures.py (Stripe/PayPal verification helpers)
  - backend/app/core/tenant_context.py (tenant lookup for webhook secrets via security.resolve_tenant_webhook_secrets)
  - alembic/versions/007_skeldir_foundation/202601211900_b057_p3_webhook_tenant_secret_resolver.py
  - alembic/versions/005_webhook_secrets/202511171000_add_webhook_secrets.py
- Auth JWKS (unrelated to platform credential substrate):
  - backend/app/security/auth.py (JWT JWKS verification)
- No OAuth client credentials or platform token storage in backend/app paths.

Conclusion:
- Existing integration substrate is limited to webhook secrets for Stripe/PayPal/Shopify/WooCommerce; no OAuth/API credential storage or platform account binding is present.

## Step C — Config surface verification

Commands:
- Get-Content backend/app/core/config.py
- Get-Content .env.example

Findings:
- backend/app/core/config.py includes DB, tenant auth header, JWT auth, app, ingestion TTL, and Celery settings only.
- .env.example includes DB, tenant auth header, JWT auth, app settings, ingestion TTL, and Celery metrics placeholders.
- No platform OAuth client ID/secret, no platform API key placeholders, and no encryption key for at-rest token storage.

Conclusion:
- Config surface for platform credential substrate is absent.

## Step D — DB schema reality (models + migrations)

Commands:
- Get-ChildItem backend/app/models | Select-Object Name
- rg -n "platform|credential|oauth|token|connection" alembic/versions

Findings:
- backend/app/models contains only: attribution_event, channel_taxonomy, dead_event, llm, base.
- No model or migration defines platform connection/credential tables.
- Existing credential-like data in DB is limited to tenants webhook secret columns (see migration 005_webhook_secrets and security.resolve_tenant_webhook_secrets).

Conclusion:
- No tenant-scoped platform connection or credential storage tables exist; only webhook secrets for inbound verification.

## Step E — CI topology (tests + required checks)

Commands:
- rg -n "pytest" .github/workflows
- Get-Content .github/workflows/b06_phase0_adjudication.yml
- rg -n "b06|b060" .github/workflows/ci.yml

Findings:
- b06_phase0_adjudication.yml runs:
  - pytest -q tests/test_b06_realtime_revenue_v1.py
  - pytest -v --tb=short tests/test_b060_phase1_auth_tenant.py
  - pytest -q tests/contract/test_contract_semantics.py
- ci.yml includes a section that runs B0.6 tests (same files) within broader CI, but no Phase 2 tests exist yet.
- Branch protection required check list (main) only includes "B0.6 Phase 0 Adjudication".

Conclusion:
- CI currently runs Phase 0/Phase 1 tests, but there is no Phase 2 test job or required status check yet.

## Hypothesis status (BH2)

- BH2-1 (No platform credentials in settings/config): CONFIRMED (no fields in config.py or .env.example).
- BH2-2 (No tenant?platform account binding model/table): CONFIRMED (no models/migrations for platform accounts).
- BH2-3 (No secure credential storage in Postgres): CONFIRMED (no tables for platform tokens; only webhook secrets on tenants).
- BH2-4 (No credential retrieval API/service): CONFIRMED (no PlatformCredentialProvider/PlatformClient substrate).
- BH2-5 (No CI governance for Phase 2): CONFIRMED (only B0.6 Phase 0 adjudication required check).

## Root-cause hypotheses (RH2) evidence alignment

- RH2-1 (integration deferred): Supported by absence of config/schema/service layer.
- RH2-2 (integration primitives exist but hidden): Partially refuted; only webhook secret handling exists.
- RH2-3 (security constraints prevented storage design): Plausible; no encryption key or token storage exists.
- RH2-4 (RLS plumbing exists but no credential table): Supported; tenant GUC/RLS plumbing exists but no platform tables.
