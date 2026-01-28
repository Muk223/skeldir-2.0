# B0.6 Phase 2 Remediation Evidence

Date: 2026-01-28

## SHAs
- Before (baseline): ed1d62841aa534eb9194c5caeb4355b1c580ca3c
- After: working tree (uncommitted changes)

## Files changed
- .env.example
- api-contracts/openapi/v1/attribution.yaml
- api-contracts/dist/openapi/v1/attribution.bundled.yaml
- backend/app/core/config.py
- backend/app/main.py
- backend/app/models/__init__.py
- backend/app/models/platform_connection.py
- backend/app/models/platform_credential.py
- backend/app/schemas/attribution.py
- backend/app/api/platforms.py
- backend/app/services/platform_connections.py
- backend/app/services/platform_credentials.py
- alembic/versions/007_skeldir_foundation/202601281200_b060_phase2_platform_connections.py
- .github/workflows/b060_phase2_adjudication.yml
- tests/test_b060_phase2_platform_connections.py

## Migration
- ID: 202601281200
- File: alembic/versions/007_skeldir_foundation/202601281200_b060_phase2_platform_connections.py
- Summary:
  - Creates platform_connections and platform_credentials tables
  - Enables pgcrypto extension for token encryption
  - Enforces RLS with tenant isolation policies
  - Adds indexes and grants for app_rw/app_ro/app_user (if present)

## Tests
- Local (Phase 2):
  - pytest -v tests/test_b060_phase2_platform_connections.py
  - Result: PASSED (2 passed). Warnings: pydantic Field(example) deprecations and alembic config deprecations.

## Local setup notes
- Installed deps: pip install -r backend/requirements.txt -r backend/requirements-dev.txt

## CI
- Phase 2 adjudication workflow added: .github/workflows/b060_phase2_adjudication.yml
- Required checks update attempt:
  - gh api PUT /branches/main/protection/required_status_checks -> 404 (insufficient permissions or endpoint access)

## Gate Evidence (pending)
- P2-F (CI execution): Pending CI run (no run link yet)
- P2-G (required check): Pending branch protection update (API call returned 404)

## Secrets handling confirmation
- API responses never return access_token or refresh_token fields.
- Token storage uses pgcrypto encryption at rest (encrypted_access_token/refresh_token BYTEA).
