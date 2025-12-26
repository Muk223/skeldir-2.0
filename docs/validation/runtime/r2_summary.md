# R2 Data-Truth Hardening Validation Summary

## Mission Statement

Prove "truth is protected at runtime" with two simultaneous guarantees:
1. **DB prevents violations** (RLS + triggers + privileges)
2. **Application never attempts destructive writes** to immutable tables

## Proof Hierarchy (Non-Negotiable)

| Level | Gate | Description |
|-------|------|-------------|
| **PRIMARY BLOCKER** | EG-R2-FIX-3 | Runtime innocence via DB statement capture (Postgres logs) |
| **CO-PRIMARY BLOCKER** | EG-R2-FIX-4 | Static behavioral innocence (whole-repo analysis) |
| Anti-Theater | EG-R2-FIX-5 | Canary injection proves detector is not broken |

**Critical:**
- Both EG-R2-FIX-3 (runtime via DB logs) AND EG-R2-FIX-4 (static) must pass
- Runtime testing is probabilistic - static audit covers latent code paths
- App/ORM layer hooks (SQLAlchemy) are NEVER authoritative - only DB logs are

### What This Means

1. **EG-R2-FIX-3 (DB Logs)**: Parses actual Postgres server logs (`log_statement=all`). Counts all statements that hit the DB. MATCH_COUNT=0 for destructive on immutable AND TOTAL_STATEMENTS>0 required.

2. **EG-R2-FIX-4 (Static Audit)**: Whole-repo grep for UPDATE/DELETE/TRUNCATE on immutable tables. Proves no latent code paths exist that could produce violations.

3. **EG-R2-FIX-5 (Canary)**: Injects deliberate violations, verifies detector catches them, removes them. Proves the static detector is not broken (anti-theater).

## Exit Gates

| Gate | Description | Status |
|------|-------------|--------|
| EG-R2-0 | Evidence anchoring & closed-set declaration | PASS |
| EG-R2-1 | RLS forced + cross-tenant denial (DB-level proof) | PASS |
| EG-R2-2 | Tenant context discipline (API + Celery) | PASS |
| EG-R2-3 | PII defense-in-depth (DB trigger enforcement) | PASS |
| EG-R2-4 | DB immutability enforcement (UPDATE/DELETE denied) | PASS |
| EG-R2-FIX-1 | DB capture enablement proof (log_statement=all) | PASS |
| EG-R2-FIX-2 | Runtime scenario suite (6 scenarios executed) | PASS |
| **EG-R2-FIX-3** | **Runtime innocence via DB logs (PRIMARY BLOCKER)** | PASS |
| **EG-R2-FIX-4** | **Static behavioral innocence (CO-PRIMARY BLOCKER)** | PASS |
| EG-R2-FIX-5 | Canary injection (anti-theater proof) | PASS |
| EG-R2-FIX-6 | DB refusal regression check (RLS + triggers) | PASS |
| EG-R2-FIX-7 | Human-readable truth record | PASS |

### Passing Run Anchor

- **Run ID:** [20526535769](https://github.com/Muk223/skeldir-2.0/actions/runs/20526535769)
- **SHA:** `7eac51d`
- **Status:** SUCCESS (All gates passed including EG-R2-FIX-3 and EG-R2-FIX-4)
- **Date:** 2025-12-26T17:29:11Z

**Runtime Innocence Verdict:**
- `TOTAL_DB_STATEMENTS_CAPTURED=2` (> 0, proving DB capture works)
- `MATCH_COUNT=0` (no destructive statements on immutable tables)
- **Canary Detection:** 3/3 patterns detected (anti-theater verified)

## Closed Sets (Derived from canonical_schema.sql)

### Tenant-Scoped Tables (15 tables with RLS)

Tables with `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + `tenant_isolation_policy`:

1. `attribution_allocations`
2. `attribution_events`
3. `budget_optimization_jobs`
4. `channel_assignment_corrections`
5. `dead_events`
6. `explanation_cache`
7. `investigation_tool_calls`
8. `investigations`
9. `llm_api_calls`
10. `llm_monthly_costs`
11. `llm_validation_failures`
12. `pii_audit_findings`
13. `reconciliation_runs`
14. `revenue_ledger`
15. `revenue_state_transitions`

### Immutable Tables (2 tables with prevent_mutation triggers)

Tables protected by `BEFORE DELETE OR UPDATE` triggers:

1. `attribution_events` - `trg_events_prevent_mutation` -> `fn_events_prevent_mutation()`
2. `revenue_ledger` - `trg_ledger_prevent_mutation` -> `fn_ledger_prevent_mutation()`

### PII-Guarded Tables (3 tables with PII triggers)

Tables protected by `BEFORE INSERT` PII guardrail triggers:

1. `attribution_events` - `trg_pii_guardrail_attribution_events`
2. `dead_events` - `trg_pii_guardrail_dead_events`
3. `revenue_ledger` - `trg_pii_guardrail_revenue_ledger`

### PII Key Blocklist (13 keys)

Keys blocked by `fn_detect_pii_keys()`:

- `email`
- `email_address`
- `phone`
- `phone_number`
- `ssn`
- `social_security_number`
- `ip_address`
- `ip`
- `first_name`
- `last_name`
- `full_name`
- `address`
- `street_address`

## Tenant Context Discipline

### API Layer (`backend/app/core/tenant_context.py`)

- `derive_tenant_id_from_request()`: Derives tenant_id from JWT or API key
- `set_tenant_context_on_session()`: Uses `SET LOCAL app.current_tenant_id`
- `tenant_context_middleware()`: FastAPI middleware for automatic context injection

### Celery Layer (`backend/app/tasks/context.py`)

- `@tenant_task` decorator: Enforces tenant_id presence in all tasks
- `_set_tenant_guc_global()`: Sets GUC using shared engine
- Uses `SET LOCAL` semantics for transaction scoping

## Defense Layers

### Layer 1: Application Code
- Tenant ID derived from authenticated request
- Tenant context set before any DB operation
- No UPDATE/DELETE patterns on immutable tables (proven by EG-R2-FIX-4)

### Layer 2: Database Triggers
- PII guardrail triggers on INSERT
- Immutability triggers on UPDATE/DELETE
- Both fire BEFORE operation (not AFTER)

### Layer 3: RLS Policies
- All tenant-scoped tables have RLS ENABLE + FORCE
- Policy: `tenant_id = current_setting('app.current_tenant_id')::uuid`
- WITH CHECK clause ensures INSERT compliance

### Layer 4: Privilege Grants
- App role has SELECT, INSERT on immutable tables
- UPDATE, DELETE revoked (defense-in-depth)

## CI Workflow

File: `.github/workflows/r2-data-truth-hardening.yml`

Triggers:
- Push to main (paths: db/schema/**, backend/app/**)
- Manual dispatch

Uses:
- Digest-pinned Postgres: `postgres@sha256:b3968e348b48f1198cc6de6611d055dbad91cd561b7990c406c3fc28d7095b21`
- Postgres started with `-c log_statement=all` for DB-level statement capture
- Canonical schema: `db/schema/canonical_schema.sql`

## Validation Evidence

Evidence artifacts are uploaded to GitHub Actions with 90-day retention:
- `R2_ENV_SNAPSHOT.json`: Environment provenance
- `CLOSED_SET_*.txt`: Derived closed sets
- `SCHEMA_FINGERPRINT.txt`: SHA256 of canonical schema
- `RLS_PROOF/*`: RLS verification logs
- `PII_PROOF/*`: PII trigger test logs
- `IMMUTABILITY_PROOF/*`: Immutability test logs
- `DB_STATEMENT_CAPTURE/*`: Postgres log parsing results (AUTHORITATIVE)
- `BEHAVIORAL_AUDIT/*`: Static analysis results
- `ADVERSARIAL_PROBE/*`: Attack simulation logs
- `R2_TRUTH_RECORD.md`: Human-readable summary

## Remediation Policy

If any gate fails:
1. DO NOT merge to main
2. Fix the issue in code/schema
3. Re-run the workflow
4. All gates must pass for R2 COMPLETE

**Hard Fail Conditions:**
- `TOTAL_DB_STATEMENTS_CAPTURED=0` → Theater detected (DB logs not working)
- `MATCH_COUNT>0` in EG-R2-FIX-3 → Runtime violation found
- Any match in EG-R2-FIX-4 → Latent code path violation

**Both EG-R2-FIX-3 AND EG-R2-FIX-4 must pass.** They are orthogonal proofs - runtime testing is probabilistic, static analysis covers latent paths.

---

*Last updated: 2025-12-26 - R2 COMPLETE (Run 20526535769, SHA 7eac51d) - Authoritative DB-level innocence proof implemented*
