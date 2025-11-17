# Contract Change Pull Request

## Description

Brief description of the contract changes in this PR.

## Change Type

- [ ] Breaking change (major version bump)
- [ ] Additive change (minor version bump)
- [ ] Documentation update (patch version bump)

## Contract Files Modified

- `api-contracts/openapi/v1/[domain].yaml`
- `api-contracts/openapi/v1/[other-domain].yaml`

## Checklist

### Validation

- [ ] Contract passes local validation (`openapi-generator-cli validate`)
- [ ] No breaking changes detected (or breaking changes are intentional)
- [ ] Version bumped appropriately (semver)
- [ ] All CI checks pass

### Documentation

- [ ] README updated (if needed)
- [ ] CHANGELOG.md updated
- [ ] Migration guide created (if breaking change)
- [ ] Privacy constraints documented (for webhooks)

### Examples

- [ ] Examples included for new endpoints
- [ ] Error examples updated (if needed)
- [ ] Request/response examples complete

### Review

- [ ] CODEOWNERS notified
- [ ] FE lead notified (if breaking change or FE impact)
- [ ] Architecture lead notified (if breaking change)

## Breaking Changes (if applicable)

### Migration Guide

- [ ] Migration guide created: `api-contracts/MIGRATION_TEMPLATE.md`
- [ ] 30-day notice period planned
- [ ] Stakeholders notified

### Impact Summary

- Endpoints removed: `[list]`
- Fields removed: `[list]`
- Type changes: `[list]`
- Other breaking changes: `[describe]`

## FE Impact Assessment

- [ ] Requires frontend SDK changes
- [ ] Requires frontend API integration changes
- [ ] No frontend impact

## Testing Evidence

- Local validation output: `[paste output]`
- Breaking change check: `[paste output]`
- Model generation: `[paste output]`

## Related Issues

Closes #[issue-number]

## Schema Changes (if applicable)

**⚠️ REQUIRED FOR ALL PRs THAT MODIFY `alembic/versions/**` OR `db/schema/**`**

### Schema Validation Checklist

- [ ] Schema validator passes locally: `python scripts/validate-schema-compliance.py`
- [ ] CI schema validation check passes (no BLOCKING divergences)
- [ ] Migration includes proper rollback (`downgrade()` function)
- [ ] All new columns have INVARIANT tags in comments
- [ ] All constraints properly named per DDL lint rules
- [ ] All Alembic migrations pass `scripts/validate-migration.sh` (no destructive DDL)
- [ ] If migration contains destructive operations, ADR documented and `# CI:DESTRUCTIVE_OK` comment added

### Downstream Readiness Verification

**This section is NON-NEGOTIABLE. This PR cannot be merged until complete.**

This PR implements requirements for Phase **B0.3** (or later). I have empirically verified:

- [ ] **B0.4 Ingestion Service**
    - [ ] INSERTs into `attribution_events` with `idempotency_key`, `event_type`, `channel` - **Verified**
    - [ ] `session_id NOT NULL` constraint enforced - **Verified**
    - [ ] `tenants.api_key_hash` exists for authentication - **Verified**

- [ ] **B0.5 Background Workers**
    - [ ] SELECTs from `attribution_events` WHERE `processing_status = 'pending'` - **Verified**
    - [ ] Index `idx_events_processing_status` exists - **Verified**

- [ ] **B1.2 API Authentication**
    - [ ] SELECTs from `tenants` WHERE `api_key_hash = ?` - **Verified**
    - [ ] UNIQUE constraint on `api_key_hash` enforced - **Verified**

- [ ] **B2.1 Statistical Attribution**
    - [ ] INSERTs into `attribution_allocations` with `confidence_score`, `model_type` - **Verified**
    - [ ] CHECK constraint on `confidence_score` (0-1) enforced - **Verified**

- [ ] **B2.2 Webhook Ingestion**
    - [ ] INSERTs into `revenue_ledger` with `transaction_id`, `state`, `currency` - **Verified**
    - [ ] UNIQUE constraint on `transaction_id` enforced - **Verified**

- [ ] **B2.3 Currency Conversion**
    - [ ] `revenue_ledger.currency` column exists (VARCHAR(3)) - **Verified**
    - [ ] `attribution_events.currency` column exists (VARCHAR(3)) - **Verified**

- [ ] **B2.4 Refund Tracking**
    - [ ] `revenue_ledger.state` column exists with CHECK constraint - **Verified**
    - [ ] `revenue_state_transitions` table exists - **Verified**
    - [ ] FK from `revenue_state_transitions.ledger_id` to `revenue_ledger.id` with CASCADE - **Verified**

### Schema Validation Evidence

**Paste validator output here:**

```json
{
  "status": "PASS",
  "summary": {
    "blocking": 0,
    "high": 0
  }
}
```

**Or attach validation_results.json artifact from CI run**

## Additional Context

Add any other context, screenshots, or examples about the PR.

