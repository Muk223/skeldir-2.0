# R2 Data-Truth Hardening Validation Summary

## Mission Statement

Prove "truth is protected at runtime" with two simultaneous guarantees:
1. **DB prevents violations** (RLS + triggers + privileges)
2. **Application never attempts destructive writes** to immutable tables

## Proof Hierarchy (Non-Negotiable)

| Level | Gate | Description |
|-------|------|-------------|
| **PRIMARY BLOCKER** | EG-R2-FIX-A | Runtime innocence via DB statement capture (Postgres logs) |
| **CO-PRIMARY BLOCKER** | EG-R2-FIX-4 | Static behavioral innocence (whole-repo analysis) |
| Anti-Theater | EG-R2-FIX-5 | Canary injection proves detector is not broken |

**Critical:**
- Both EG-R2-FIX-A (runtime via DB logs) AND EG-R2-FIX-4 (static) must pass
- Runtime testing is probabilistic - static audit covers latent code paths
- App/ORM layer hooks (SQLAlchemy) are NEVER authoritative - only DB logs are

### What This Means

1. **EG-R2-FIX-A (DB Logs)**: Parses actual Postgres server logs (`log_statement=all`) with **window + per-scenario delimiters**. Requires markers present, each scenario has ≥1 non-marker statement, and `MATCH_COUNT_DESTRUCTIVE_ON_IMMUTABLE=0`.

2. **EG-R2-FIX-4 (Static Audit)**: Whole-repo scan (AST + literal SQL) for destructive patterns/constructs targeting immutable tables, with an explicit scope manifest + scope hash.

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
| **EG-R2-FIX-B** | **Scenario suite hard gate (PRIMARY BLOCKER)** | PENDING (requires fresh CI run) |
| **EG-R2-FIX-A** | **DB window-delimited runtime innocence (PRIMARY BLOCKER)** | PENDING (requires fresh CI run) |
| **EG-R2-FIX-4** | **Static behavioral innocence (CO-PRIMARY BLOCKER)** | PENDING (requires fresh CI run) |
| **EG-R2-FIX-5** | **Canary integrity (anti-theater proof)** | PENDING (requires fresh CI run) |
| EG-R2-FIX-6 | DB refusal regression check (RLS + triggers) | PASS |
| EG-R2-FIX-7 | Human-readable truth record | PASS |

## Current Status: BLOCKED (Evidence Drift / False-Green Risk)

Prior “passing” runs are not acceptable as authoritative R2 proof because they allowed false-green failure modes:

- Scenario suite was not proven as a hard gate (executed != passed must fail the phase).
- DB statement capture could be mis-scoped/mis-counted (internally inconsistent totals), compatible with capturing only boot/preflight.
- Canary “proof” could be satisfied without running the detector.

R2 is COMPLETE only after a single CI run on the candidate SHA shows all required verdict blocks browser-visible and internally consistent.

## What Changed (R2 Hardening)

- **Scenario suite is a hard gate** via `scripts/r2/runtime_scenario_suite.py` (6 scenarios, per-scenario DB markers, exits non-zero on any failure).
- **Authoritative DB capture is window-delimited and per-scenario verified** via `scripts/r2/db_log_window_audit.py` parsing Postgres `docker logs`.
- **Static behavioral audit is independent and explicit** via `scripts/r2/static_behavioral_audit.py` (scope manifest + scope hash + reviewed allowlist file).
- **Anti-theater canary is real**: the static audit must fail when a canary is injected and pass after removal (CI workspace only).

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
- `SCENARIOS_PASSED != SCENARIOS_EXECUTED` (scenario suite hard gate)
- Missing window/per-scenario markers or any scenario with `NON_MARKER_STATEMENTS_COUNT == 0` (theater window)
- `TOTAL_DB_STATEMENTS_CAPTURED_IN_WINDOW < (2 * num_scenarios + 2)` (marker/parsing drift)
- `MATCH_COUNT_DESTRUCTIVE_ON_IMMUTABLE > 0` in the authoritative DB window
- Static audit detects destructive patterns/constructs targeting immutable tables
- Canary does not force a fail when injected (detector integrity failure)

**Both EG-R2-FIX-A AND EG-R2-FIX-4 must pass.** They are orthogonal proofs - runtime testing is probabilistic, static analysis covers latent paths.

---

*Last updated: 2025-12-27 - R2 hardening implemented; awaiting a fresh CI run anchored to candidate SHA to declare R2 COMPLETE.*
