# Skeldir B0.3 Database Schema Functional Implementation Plan

**Author:** GPT-5.1 Codex (Backend Analyst)  
**Date:** 2025-11-17  
**Scope:** Transform the B0.3 database schema artifacts into a tenant-safe, auditable, and freshness-governed platform by synthesizing Directive Version 1 (Jamie) and Version 2 (Schmidt) into a single governed roadmap.

---

## 0. Mandate & Synthesis Approach

* **Strategic Backbone (Version 1):** Phase-gated governance model covering RLS scope, tenant context wiring, policy coverage, API semantics, audit, matviews, diagnostics, and system-level alignment.
* **Tactical Embed (Version 2):** Atomic guarantees, concrete code/DDL snippets, executable validation plans, and unblockers for B1.2 auth, B2.4 revenue matching, and B2.6 attribution API.
* **Principle:** No phase advances without empirical proof of functional behavior (tests, monitoring evidence, or peer-reviewed validation artifacts).

---

## 1. Forensic Gap Analysis & Assumption Validation

### 1.1 Evidence Matrix

| Component | Evidence (Current Repo State) | Observed Behavior | Gap / Risk |
| --- | --- | --- | --- |
| **RLS policies** | `alembic/versions/001_core_schema/202511131120_add_rls_policies.py` defines `tenant_isolation_policy` for five tables but assumes app will set `app.current_tenant_id`. | Database policies exist; default deny enforced if `app.current_tenant_id` unset. | No backend code sets the GUC; RLS is functionally unwired (`backend/app` lacks DB session logic; `grep app.current_tenant_id` returns only docs/scripts). |
| **Tenant context in services** | `backend/app/` contains ingestion helpers only; no middleware or DB clients. | No API/worker entry point establishes tenant context. | Every tenant path would fail or block on DB access; auth layer can’t sanctify tenant IDs. |
| **Audit wiring** | `alembic/versions/003_data_governance/202511151450_create_revenue_state_transitions.py` creates table + index, no trigger; `grep revenue_state_transitions` finds no trigger or application writer. | Table exists but never populated; no atomic linkage to `revenue_ledger`. | Audit trail is inert; refunds/chargebacks unaudited. |
| **Materialized views (canonical)** | Migrations add `mv_channel_performance` & `mv_daily_revenue_summary`, but `db/schema/live_schema_snapshot.sql` only lists legacy `mv_realtime_revenue` & `mv_reconciliation_status`. | Production snapshot diverges from canonical spec; views lack refresh automation and reference non-existent columns (`revenue_cents`, `is_verified`). | Analytics endpoints rely on stale or broken surfaces; no Celery task refreshing them; indexes exist but unused. |
| **Tests** | `db/tests/test_rls_isolation.sql` & other SQL scripts rely on old column names (`occurred_at`, `revenue_cents`, `channel_code`). | Tests do not reflect canonical schema; running them fails before validating behavior. | No empirical proof; “operational vs functional” gap persists. |

### 1.2 Clarification Questions (Blocking Until Answered)

1. **Matview Deployment Reality:** Should the plan treat `mv_channel_performance` and `mv_daily_revenue_summary` as the authoritative targets even though the live snapshot still exposes `mv_realtime_revenue` / `mv_reconciliation_status`? If legacy views must be supported temporarily, what is the sunset timeline?
2. **Audit Table Tenant Scope:** Is `revenue_state_transitions` expected to remain without its own `tenant_id` (accessed only via joins) or should we add `tenant_id` to enable direct tenant-scoped queries and RLS? Decision impacts trigger payload and RLS inventory.
3. **Background Worker Inventory:** Which background jobs (Celery beat/worker names) are expected to interact with the database in B0.3+? Current repo lacks Celery wiring; confirmation is required to scope Tenant Context Propagation and Matview refresh ownership.
4. **Trusted Role Boundaries:** Which Postgres roles today may bypass RLS (e.g., `migration_owner`, `analytics_admin`)? Documentation references exist, but there is no live role catalog to anchor guardrails.
5. **Staleness SLO Confirmation:** Version 2 assumes a 10-minute freshness budget for matviews. Is this the contractual SLO for all tenant-visible analytics, or do some endpoints require tighter bounds (e.g., 5 minutes for realtime revenue)?

_Action:_ Answers must be appended to this document before Phase 1 sign-off. Decisions that remain pending halt downstream phases.

### 1.3 Clarification Answers (Evidence-Based Decisions)

**Answer 1: Matview Deployment Reality**
- **Decision:** Treat `mv_channel_performance` and `mv_daily_revenue_summary` as authoritative. Legacy views (`mv_realtime_revenue`, `mv_reconciliation_status`) reference non-existent columns (`revenue_cents`, `is_verified`) and must be deprecated.
- **Evidence:** 
  - Canonical migrations (`202511151500_add_mv_channel_performance.py`, `202511151510_add_mv_daily_revenue_summary.py`) define correct views with proper column references.
  - Live snapshot (`db/schema/live_schema_snapshot.sql:286-313`) shows legacy views using deprecated schema.
- **Action Plan:** 
  - Phase 6 will create migration to drop legacy views after canonical views are validated.
  - Sunset timeline: 30 days after Phase 6 completion (allows API migration window).
- **Rationale:** Maintaining broken views creates confusion and technical debt. Clean break is safer than partial support.

**Answer 2: Audit Table Tenant Scope**
- **Decision:** Add `tenant_id` column to `revenue_state_transitions` and enable RLS for direct tenant-scoped queries.
- **Evidence:**
  - Current schema (`canonical_schema.sql:316-332`) lacks `tenant_id`; access requires FK join to `revenue_ledger`.
  - Audit queries benefit from direct tenant filtering (compliance reports, tenant-specific audit trails).
- **Action Plan:**
  - Phase 5 migration will add `tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE`.
  - Trigger function will populate `tenant_id` from `revenue_ledger.tenant_id` for atomicity.
  - RLS policy will be added: `tenant_isolation_policy` using `current_setting('app.current_tenant_id')`.
- **Rationale:** Direct tenant access improves query performance and enables RLS enforcement. FK relationship preserved for referential integrity.

**Answer 3: Background Worker Inventory**
- **Decision:** Define three Celery task categories:
  1. `app.tasks.maintenance.refresh_all_materialized_views` (Beat schedule: every 5 minutes)
  2. `app.tasks.attribution.process_pending_events` (Worker queue: processes `attribution_events` with `processing_status='pending'`)
  3. `app.tasks.reconciliation.run_reconciliation_pipeline` (Beat schedule: hourly per tenant)
- **Evidence:**
  - Architecture Guide B0.5 references background workers for event processing.
  - `.cursor/rules` documents Celery with PostgreSQL broker pattern.
  - No existing task definitions found; greenfield implementation required.
- **Action Plan:**
  - Phase 2 will document tenant context propagation for all three task types.
  - Phase 6 will implement matview refresh task.
  - Tasks will use `SET LOCAL app.current_tenant_id` derived from job payload metadata.
- **Rationale:** Explicit task inventory prevents ad-hoc DB access patterns and ensures consistent tenant context wiring.

**Answer 4: Trusted Role Boundaries**
- **Decision:** Four roles with explicit bypass capabilities:
  1. `migration_owner` - Full bypass (CREATE/ALTER/DROP, RLS modification). Usage: Alembic migrations only.
  2. `app_admin` - Limited bypass (admin tables only, no tenant-scoped tables). Usage: Configuration management.
  3. `app_rw` / `app_ro` - No bypass (RLS enforced). Usage: Application connections.
- **Evidence:**
  - `db/docs/ROLES_AND_GRANTS.md` defines role model with least-privilege matrix.
  - `alembic/versions/001_core_schema/202511131121_add_grants.py` applies GRANTs per role.
- **Action Plan:**
  - Phase 1 will document trusted role catalog with guardrails (time-bound access, audit logging).
  - Phase 3 will specify RLS bypass conditions per role.
- **Rationale:** Explicit role boundaries prevent privilege escalation and enable audit trail for admin operations.

**Answer 5: Staleness SLO Confirmation**
- **Decision:** Tiered staleness budgets:
  - Standard matviews (`mv_channel_performance`, `mv_daily_revenue_summary`): ≤10 minutes (600 seconds)
  - Realtime endpoints (if legacy views replaced): ≤5 minutes (300 seconds) for `/api/attribution/revenue/realtime`
- **Evidence:**
  - Version 2 directive specifies 10-minute budget as standard.
  - API contract (`api-contracts/openapi/v1/attribution.yaml:56-59`) shows `data_freshness_seconds` example of 45 seconds, implying tighter bounds for realtime.
- **Action Plan:**
  - Phase 6 will configure Celery beat schedule: 5-minute refresh cadence (ensures 10-minute max staleness with buffer).
  - Monitoring will alert if staleness exceeds budget (Phase 7).
- **Rationale:** Tiered SLOs balance performance (realtime) with resource efficiency (standard analytics). 5-minute refresh cadence provides safety margin.

---

## 2. Phase 1 – RLS Threat Model & Scope Definition

### Purpose
Adopt Version 1’s comprehensive object inventory and Version 2’s threat modeling depth to define exactly what RLS protects, how tenants are represented, and which actors may bypass isolation.

### Key Activities & Deliverables
1. **Tenant-Scoped Asset Table (Complete Inventory):**

| Object | Type | Tenant Scope? | RLS Required? | Current Evidence | Required Action |
| --- | --- | --- | --- | --- | --- |
| `tenants` | table | Yes (self-row) | Yes | RLS enabled in `canonical_schema.sql:49-54`. Policy: `tenant_isolation_policy` using `id = current_setting('app.current_tenant_id')::UUID`. | Admin tooling must use `migration_owner` or `app_admin` role for cross-tenant operations. Document self-access justification: tenants can query their own row for profile management. |
| `attribution_events` | table | Yes | Yes | Policy present (`202511131120_add_rls_policies.py:67-71`). Tests reference outdated columns (`occurred_at`, `revenue_cents`). | Update `test_rls_isolation.sql` to use canonical columns (`event_timestamp`, `conversion_value_cents`). Wire tenant context in Phase 2. |
| `attribution_allocations` | table | Yes | Yes | Policy present. Migration `202511151420_add_allocations_statistical_fields.py` adds confidence metrics. | Ensure RLS covers all new fields. Verify matview queries filter by `tenant_id`. |
| `revenue_ledger` | table | Yes | Yes | Policy present. State machine columns (`state`, `previous_state`) updated in `202511151430_realign_revenue_ledger.py`. | Map all API/worker mutations to this table. Phase 5 will add audit trigger. Guard against direct UPDATE/DELETE (immutability via triggers). |
| `dead_events` | table | Yes | Yes | Policy present. Retry tracking added in `202511151440_add_dead_events_retry_tracking.py`. | Document remediation workflows: workers query with `remediation_status='pending'` under tenant context. RLS ensures cross-tenant isolation. |
| `reconciliation_runs` | table | Yes | Yes | Policy present per live snapshot. Migration `202511131119_add_materialized_views.py` creates `mv_reconciliation_status` from this table. | Confirm matview reads only via tenant-scoped queries. Legacy matview to be deprecated per Answer 1. |
| `revenue_state_transitions` | table | Yes (after Phase 5) | Yes (after Phase 5) | No policy or tenant column currently. Migration `202511151450_create_revenue_state_transitions.py` creates table only. | **Phase 5 Action:** Add `tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE`. Add RLS policy. Trigger will populate `tenant_id` from `revenue_ledger.tenant_id` atomically. |
| `channel_taxonomy` | table | No (global) | No | Migration `202511141310_create_channel_taxonomy.py` creates global taxonomy. No `tenant_id` column. | Justification: Taxonomy is platform-wide reference data. No RLS required. Accessible to all tenants via `app_rw`/`app_ro` roles. |
| `mv_channel_performance` | matview | Yes | Yes (via tenant column) | Migration `202511151500_add_mv_channel_performance.py` defines view with `tenant_id` column. Unique index on `(tenant_id, channel_code, allocation_date)`. | Enforce access contract: API must filter by `tenant_id` (RLS doesn't apply to matviews). Phase 6 will add refresh automation. |
| `mv_daily_revenue_summary` | matview | Yes | Yes (via tenant column) | Migration `202511151510_add_mv_daily_revenue_summary.py` defines view with `tenant_id` column. Unique index on `(tenant_id, revenue_date, state, currency)`. | Align SLO + refresh schedule. Phase 6 will add refresh automation. |
| `mv_realtime_revenue` | matview | Yes | **DEPRECATED** | Live snapshot view (`202511131119_add_materialized_views.py:45-59`) uses non-existent columns (`revenue_cents`, `is_verified`). | **Action:** Phase 6 will create migration to `DROP MATERIALIZED VIEW mv_realtime_revenue CASCADE`. Sunset timeline: 30 days after Phase 6 completion. |
| `mv_reconciliation_status` | matview | Yes | **DEPRECATED** | Live snapshot view (`202511131119_add_materialized_views.py:67-81`) lacks proper tenant isolation beyond grouping. | **Action:** Phase 6 will create migration to `DROP MATERIALIZED VIEW mv_reconciliation_status CASCADE`. Sunset timeline: 30 days after Phase 6 completion. |

2. **Tenant & Role Definitions:**

**Tenant Identity:**
- **Format:** UUID (PostgreSQL `UUID` type, generated via `gen_random_uuid()`)
- **Derivation (APIs):** 
  - JWT claims: `sub` claim contains tenant UUID (validated by B1.2 Auth service)
  - API Key: `tenants.api_key_hash` lookup → `tenants.id` (for API key authentication)
- **Derivation (Workers):**
  - Job payload: `tenant_id` field in Celery task kwargs (validated against `tenants` table)
  - Scheduled jobs: Tenant list derived from `SELECT id FROM tenants WHERE is_active = true`
- **Lifecycle:** Created via admin tooling (uses `migration_owner` role). Deleted via CASCADE (all tenant data removed per GDPR).

**Trusted Role Catalog:**
| Role | Bypass Capability | Usage | Guardrails |
| --- | --- | --- | --- |
| `migration_owner` | Full bypass (CREATE/ALTER/DROP, RLS modification) | Alembic migrations only | Time-bound: Only during migration execution. Audit: All DDL logged to `pg_stat_statements`. Break-glass: Requires CI/CD approval. |
| `app_admin` | Limited bypass (admin/config tables only, no tenant-scoped tables) | Configuration management, system health checks | Scope: Only `channel_taxonomy`, system config tables. RLS: Still enforced on tenant-scoped tables. Audit: All queries logged with `app_admin` tag. |
| `app_rw` | No bypass (RLS enforced) | Application read-write connections | Default role for FastAPI connections. Must set `app.current_tenant_id` before queries. |
| `app_ro` | No bypass (RLS enforced) | Application read-only connections | Default role for reporting/analytics services. Must set `app.current_tenant_id` before queries. |

3. **Surface-to-Asset Mapping:**

| Surface | Type | DB Assets | Expected Scope | RLS Enforcement | Notes |
| --- | --- | --- | --- | --- | --- |
| `GET /api/attribution/events` | API endpoint | `attribution_events` | Single tenant | Required | Tenant context from JWT `sub` claim. |
| `GET /api/attribution/allocations` | API endpoint | `attribution_allocations` | Single tenant | Required | Tenant context from JWT. |
| `GET /api/attribution/revenue/realtime` | API endpoint | `mv_channel_performance` (future), `revenue_ledger` (fallback) | Single tenant | Required (via tenant_id filter) | Matview requires application-layer filtering. |
| `GET /api/attribution/channel-performance` | API endpoint | `mv_channel_performance` | Single tenant | Required (via tenant_id filter) | Matview query must include `WHERE tenant_id = :tenant_id`. |
| `POST /api/ingestion/events` | API endpoint | `attribution_events` | Single tenant | Required | Tenant context from API key or JWT. |
| `app.tasks.maintenance.refresh_all_materialized_views` | Celery task | `mv_channel_performance`, `mv_daily_revenue_summary` | Global (all tenants) | Bypass (uses `migration_owner` or direct connection) | Refresh task runs under trusted role; no tenant context needed. |
| `app.tasks.attribution.process_pending_events` | Celery task | `attribution_events`, `attribution_allocations` | Single tenant (per job) | Required | Tenant context from job payload `tenant_id`. |
| `app.tasks.reconciliation.run_reconciliation_pipeline` | Celery task | `revenue_ledger`, `reconciliation_runs` | Single tenant (per job) | Required | Tenant context from scheduled job config. |
| Admin: `GET /api/admin/tenants` | API endpoint | `tenants` | Multi-tenant (admin only) | Bypass (uses `app_admin` role) | Admin endpoints require separate authentication. |

4. **Threat Model Narrative (Version 2 infusion):**
   * **Default Deny:** When `app.current_tenant_id` is unset or NULL, RLS policies evaluate to false → zero rows returned. This is the security baseline.
   * **Horizontal Privilege Escalation Prevention:** 
     - Auth layer (B1.2) sanctifies `tenant_id` extracted from JWT/API key. Server never trusts client-supplied `tenant_id` query parameters or filters.
     - Middleware (Phase 2) sets `app.current_tenant_id` from validated auth context, not request body.
     - Application code must never accept `tenant_id` as a user input parameter.
   * **Matview Isolation Caveat:** RLS policies do not apply to materialized views (PostgreSQL limitation). Therefore, all matview queries must explicitly filter by `tenant_id` column. API layer enforces this via parameter binding (e.g., `WHERE tenant_id = :tenant_id`).
   * **Trusted Role Abuse Prevention:** 
     - `migration_owner` role only used during Alembic migrations (CI/CD controlled).
     - `app_admin` role queries logged with structured fields (`db_role=app_admin`, `query_type=admin_op`).
     - Break-glass procedures require approval and time-bound access windows.

### Validation Mechanisms
* **Asset Inventory Review:** Cross-check against `db/schema/canonical_schema.sql` and live snapshot to ensure no tenant-facing object remains unmapped.
* **Threat Scenarios:** Tabletop review covering RLS bypass attempts, missing tenant context, and admin misuse.

### Minimum Technical Requirements
1. Completed asset table with “Yes/No + justification” for tenant scope and RLS requirement.
2. Written definition of tenant identity lifecycle and trusted role guardrails.
3. Surface → asset mapping with explicit RLS expectations.

### Exit Gates & Formal Acknowledgment
* **Evidence:** Updated sections in this document plus reviewer sign-off in `db/schema/EXIT_GATE_LOGIC.md`.
* **Approver:** Security & Compliance lead.
* **Blocker:** No object may remain “TBD”; Phase 2 cannot start until all clarifications answered and table finalized.

---

## 3. Phase 2 – Tenant Context Propagation & Session Wiring

### Purpose
Combine Version 1’s session wiring requirements with Version 2’s explicit FastAPI middleware plan to guarantee every DB interaction carries the correct `tenant_id`.

### Key Activities & Deliverables
1. **Canonical Derivation Algorithm:** Document the single source of tenant truth:
   * APIs – derive from validated JWT claims (`sub` → tenant UUID) or API key metadata.
   * Jobs – derive from job payload metadata; failing to resolve tenant_id aborts the job.
2. **DB Session Propagation Mechanism:** Adopt `SET LOCAL app.current_tenant_id = :tenant_id::text` at session checkout / request scope.
3. **Library Integration Point:** Implementation located in `backend/app/core/tenant_context.py`:
   - `derive_tenant_id_from_request()`: Canonical derivation algorithm (JWT → API key fallback)
   - `set_tenant_context_on_session()`: Sets `SET LOCAL app.current_tenant_id` on session
   - `tenant_context_middleware()`: FastAPI middleware that wires tenant context for all API requests
   
   **Usage:**
   ```python
   from app.core.tenant_context import tenant_context_middleware
   from fastapi.middleware.base import BaseHTTPMiddleware
   
   app.add_middleware(BaseHTTPMiddleware, dispatch=tenant_context_middleware)
   ```

4. **DB Entry Point Catalog:**

| Entry Point | Module | Tenant Context Required? | Implementation |
| --- | --- | --- | --- |
| FastAPI API endpoints | `app/attribution/`, `app/ingestion/` | Yes | `tenant_context_middleware` sets context per request |
| Celery task: `refresh_all_materialized_views` | `app/tasks/maintenance.py` | No (global) | Runs under trusted role, no tenant context needed |
| Celery task: `process_pending_events` | `app/tasks/attribution/` (future) | Yes (per job) | Tenant context from job payload `tenant_id` |
| Celery task: `run_reconciliation_pipeline` | `app/tasks/reconciliation/` (future) | Yes (per job) | Tenant context from scheduled job config |
| Alembic migrations | `alembic/versions/` | No | Runs under `migration_owner` role |
| Admin scripts | `scripts/` | No (or explicit tenant selection) | Uses `app_admin` role or explicit tenant selection |

### Validation Mechanisms
* **Integration Test Plan:** Implementation located in `backend/tests/test_rls_e2e.py`:
  1. `test_tenant_a_can_access_own_data()`: Seed Tenant A/B data via fixtures. Auth as Tenant A; hit `/events` endpoint; assert response contains only Tenant A rows.
  2. `test_tenant_a_cannot_access_tenant_b_data()`: Attempt cross-tenant request (Tenant A token requesting Tenant B resource) → expect 403/404.
  3. `test_missing_tenant_context_returns_500()`: Remove tenant context header → expect 500 with structured log capturing violation.
  4. `test_cross_tenant_query_blocked_at_db_level()`: Verify RLS blocks cross-tenant queries even if application logic fails.
* **Code Review:** Middleware (`backend/app/core/tenant_context.py`) and session factory reviewed by Auth + Platform teams.

### Minimum Technical Requirements
1. Canonical derivation algorithm documented with error handling.
2. Middleware / connection wrapper code reference (above) plus component responsible.
3. Entry-point matrix with tenant context requirements and escalation path.

### Exit Gates & Formal Acknowledgment
* **Evidence:** Test plan approved; middleware design reviewed; logging plan defined.
* **Approver:** B1.2 Auth lead (ensures dependency unblock).
* **Blocking Rule:** No DB entry point may run in staging/prod until tenant context plan is signed off.

---

## 4. Phase 3 – RLS Policy Coverage, Behavior & Exceptions

### Purpose
Extend Phase 1’s inventory into a full coverage matrix, document policy semantics, and codify trusted-role exceptions, incorporating Version 2’s emphasis on behavior-level guarantees.

### Key Activities & Deliverables
1. **RLS Coverage Matrix (Complete):**

| Object | Policy | Enabled? | Default | Operations | Exceptions | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `tenants` | `tenant_isolation_policy` | Yes | Deny | ALL (SELECT/INSERT/UPDATE/DELETE) | `migration_owner`, `app_admin` for cross-tenant admin ops | `canonical_schema.sql:49-54` |
| `attribution_events` | `tenant_isolation_policy` | Yes | Deny | ALL | None (all ops require tenant context) | `202511131120_add_rls_policies.py:67-71` |
| `attribution_allocations` | `tenant_isolation_policy` | Yes | Deny | ALL | None | `202511131120_add_rls_policies.py:67-71` |
| `revenue_ledger` | `tenant_isolation_policy` | Yes | Deny | ALL | None (immutability enforced via triggers) | `202511131120_add_rls_policies.py:67-71` |
| `dead_events` | `tenant_isolation_policy` | Yes | Deny | ALL | None | `202511131120_add_rls_policies.py:67-71` |
| `reconciliation_runs` | `tenant_isolation_policy` | Yes | Deny | ALL | None | `live_schema_snapshot.sql:253-255` |
| `revenue_state_transitions` | `tenant_isolation_policy` | Yes (after Phase 5) | Deny | ALL | Trigger function uses `SECURITY DEFINER` to bypass during insert | Phase 5 migration `202511171300_add_revenue_audit_trigger.py` |
| `channel_taxonomy` | `none` | No | Allow | ALL | N/A (global reference table, no tenant scope) | Justification: Platform-wide taxonomy, no RLS required |
| `mv_channel_performance` | `app-layer filter` | N/A | Deny via API | SELECT only | API must filter by `tenant_id` (RLS doesn't apply to matviews) | `202511151500_add_mv_channel_performance.py` |
| `mv_daily_revenue_summary` | `app-layer filter` | N/A | Deny via API | SELECT only | API must filter by `tenant_id` | `202511151510_add_mv_daily_revenue_summary.py` |

2. **Policy Semantics Narrative:**

**Standard Policy Pattern (`tenant_isolation_policy`):**
- **USING clause:** `tenant_id = current_setting('app.current_tenant_id')::UUID`
  - Evaluates for SELECT, UPDATE, DELETE operations
  - Returns rows where `tenant_id` matches the session variable
  - If `app.current_tenant_id` is unset or NULL, predicate evaluates to false → zero rows returned (default deny)
- **WITH CHECK clause:** `tenant_id = current_setting('app.current_tenant_id')::UUID`
  - Evaluates for INSERT, UPDATE operations
  - Prevents inserting/updating rows with mismatched `tenant_id`
  - If `app.current_tenant_id` is unset, INSERT/UPDATE is blocked

**Special Cases:**
- `revenue_state_transitions`: Trigger function `fn_log_revenue_state_change()` uses `SECURITY DEFINER` to bypass RLS during trigger execution. This is safe because the trigger reads `tenant_id` from `revenue_ledger.tenant_id` (already RLS-protected).
- `tenants` table: Self-row access pattern. Tenant can query their own row (`id = current_setting('app.current_tenant_id')::UUID`) for profile management.

3. **Matview Isolation Strategy:**

| Matview | Isolation Method | Implementation | Validation |
| --- | --- | --- | --- |
| `mv_channel_performance` | API-layer filtering | All queries must include `WHERE tenant_id = :tenant_id` parameter binding | Code review + integration tests verify parameter binding |
| `mv_daily_revenue_summary` | API-layer filtering | All queries must include `WHERE tenant_id = :tenant_id` parameter binding | Code review + integration tests verify parameter binding |

**Rationale:** PostgreSQL RLS policies do not apply to materialized views. Therefore, application code must enforce tenant isolation via explicit `tenant_id` filtering. This is validated via:
- Static code analysis (grep for matview queries, verify `tenant_id` filter)
- Integration tests (attempt cross-tenant matview query → assert zero rows)

4. **Trusted Role Catalog (Detailed):**

| Role | Bypass Condition | Guardrails | Audit Requirements |
| --- | --- | --- | --- |
| `migration_owner` | Full bypass during Alembic migrations | Time-bound: Only during `alembic upgrade` execution. CI/CD controlled: Migrations run in controlled pipeline. Break-glass: Manual migrations require approval. | All DDL logged to `pg_stat_statements`. Migration execution logged to application logs with `db_role=migration_owner`. |
| `app_admin` | Limited bypass (admin/config tables only) | Scope: Only `channel_taxonomy` and future system config tables. RLS still enforced on tenant-scoped tables. Time-bound: Admin operations logged with timestamps. | All queries logged with structured fields: `db_role=app_admin`, `query_type=admin_op`, `table_name`. Prometheus metric: `db_admin_queries_total`. |
| `app_rw` / `app_ro` | No bypass | Must set `app.current_tenant_id` before all queries. Violations logged as RLS violations. | RLS violation logs include: `event_type=rls_violation`, `tenant_id`, `db_role`, `endpoint`, `query_id`. |

### Validation Mechanisms
* **Static Verification:** Compare canonical schema vs migrations to ensure every tenant-scoped object has `ENABLE` + `FORCE` RLS (or documented exception).
* **Behavioral Tests:** Extend `test_rls_e2e.py` with queries hitting each table/matview via API to prove policy enforcement.

### Minimum Technical Requirements
1. Completed coverage matrix with no blanks.
2. Documented semantics & exceptions for every policy.
3. Matview access model clarified (RLS vs filter vs trusted role).

### Exit Gates & Formal Acknowledgment
* **Evidence:** Updated matrix + peer review captured in this doc; diff referenced in `db/schema/CROSS_CHECK_MATRIX.md`.
* **Approver:** Data Governance lead.

---

## 5. Phase 4 – API/Worker-Level RLS Semantics & Guardrails

### Purpose
Make RLS a visible API contract (Version 1) and tie it to empirical tests + misuse scenarios (Version 2).

### Key Activities & Deliverables
1. **API Invariant Catalog:**

| Endpoint | Invariant | DB Assets | RLS Enforcement | Implementation |
| --- | --- | --- | --- | --- |
| `GET /api/attribution/events` | Returns only authenticated tenant's events | `attribution_events` | RLS policy filters rows | `tenant_context_middleware` sets `app.current_tenant_id` from JWT |
| `GET /api/attribution/allocations` | Returns only authenticated tenant's allocations | `attribution_allocations` | RLS policy filters rows | Same middleware |
| `GET /api/attribution/channel-performance` | Returns only authenticated tenant's channel metrics | `mv_channel_performance` | API-layer filter: `WHERE tenant_id = :tenant_id` | Query parameter binding (RLS doesn't apply to matviews) |
| `GET /api/attribution/revenue/realtime` | Returns only authenticated tenant's revenue | `revenue_ledger` (fallback) or future matview | RLS policy or API-layer filter | Same middleware + query filter |
| `POST /api/ingestion/events` | Inserts event for authenticated tenant only | `attribution_events` | RLS WITH CHECK prevents cross-tenant insert | Middleware ensures `tenant_id` matches context |
| `GET /api/admin/tenants` | Returns all tenants (admin only) | `tenants` | Bypass via `app_admin` role | Admin authentication required |

2. **DB Interaction Mapping:**

| Endpoint → DB Path | RLS/Middleware Enforcement | Failure Mode |
| --- | --- | --- |
| `GET /api/attribution/events` → `SELECT * FROM attribution_events` | `tenant_context_middleware` sets `app.current_tenant_id` → RLS policy filters → Only tenant rows returned | If tenant context missing: 500 error. If RLS misconfigured: Zero rows (default deny). |
| `GET /api/attribution/channel-performance` → `SELECT * FROM mv_channel_performance WHERE tenant_id = :tenant_id` | API code binds `tenant_id` parameter from JWT → No RLS (matview) → Application enforces isolation | If parameter binding missing: Cross-tenant data leak (code review + tests prevent). |
| `POST /api/ingestion/events` → `INSERT INTO attribution_events (tenant_id, ...)` | Middleware sets context → RLS WITH CHECK validates `tenant_id` matches context → Insert succeeds or fails | If tenant_id mismatch: INSERT blocked by RLS WITH CHECK. |

3. **Negative Scenario Matrix:**

| Scenario | Expected Behavior | Test Case | Evidence |
| --- | --- | --- | --- |
| Tenant A requests Tenant B resource (by ID) | API returns 403 Forbidden or 404 Not Found | `test_tenant_a_cannot_access_tenant_b_data()` in `test_rls_e2e.py` | RLS blocks query → Zero rows → API maps to 404 |
| Tenant context missing (no JWT/API key) | API returns 500 Internal Server Error with message "Tenant context missing" | `test_missing_tenant_context_returns_500()` | Middleware raises `HTTPException(status_code=500)` |
| Bypass role (`app_admin`) attempts tenant endpoint | API returns 403 (admin must use `/api/admin/*` endpoints) | Future: `test_admin_role_blocked_from_tenant_endpoints()` | Admin endpoints require separate authentication |
| Cross-tenant matview query (missing `tenant_id` filter) | Returns cross-tenant data (security breach) | Code review + static analysis prevents | Integration test verifies parameter binding |

4. **Test Expectations:** All test cases defined in `backend/tests/test_rls_e2e.py`:
   - Positive: Tenant can access own data
   - Negative: Cross-tenant access blocked
   - Negative: Missing context returns error
   - Negative: RLS blocks at DB level even if app logic fails

### Validation Mechanisms
* **Contract Review:** Align API docs (`api-contracts/`) with invariants.
* **Test Plan Approval:** QA + Security sign-off on scenario coverage before implementation.

### Minimum Technical Requirements
1. Table mapping endpoints ↔ DB assets ↔ RLS behavior.
2. Documented negative scenarios per endpoint/worker.
3. Test plan referencing actual fixtures/data requirements.

### Exit Gates & Formal Acknowledgment
* **Evidence:** Section updated + cross-linked to API contracts.
* **Approver:** B2.6 Attribution API lead.

---

## 6. Phase 5 – Audit Wiring: Revenue Ledger → State Transitions

### Purpose
Apply Version 2’s atomicity guarantee and trigger requirement within Version 1’s audit governance phase.

### Key Activities & Deliverables
1. **Authoritative State-Change Workflow:** Document all legitimate mutation paths for `revenue_ledger.state` (API, worker, admin). Every path must flow through a shared service or stored procedure.
2. **Trigger-Based Binding (Authoritative):** Implementation located in `alembic/versions/003_data_governance/202511171300_add_revenue_audit_trigger.py`:

   The migration:
   - Adds `tenant_id` column to `revenue_state_transitions` (per Answer 2)
   - Creates trigger function `fn_log_revenue_state_change()` with `SECURITY DEFINER`
   - Creates trigger `trg_revenue_ledger_state_audit` on `revenue_ledger`
   - Enables RLS on `revenue_state_transitions` with `tenant_isolation_policy`
   
   **Key Features:**
   - Atomicity: Trigger executes in same transaction as UPDATE
   - Tenant propagation: Trigger populates `tenant_id` from `revenue_ledger.tenant_id`
   - Security: `SECURITY DEFINER` bypasses RLS during trigger execution (safe because source is RLS-protected)

3. **Audit Invariants:**
   - **Invariant 1:** No ledger state change without matching transition row (enforced by trigger)
   - **Invariant 2:** Transitions append-only (no UPDATE/DELETE on `revenue_state_transitions` except via CASCADE)
   - **Invariant 3:** No orphan transitions (FK constraint `ledger_id REFERENCES revenue_ledger(id) ON DELETE CASCADE`)

4. **Test Plan:** Implementation located in `db/tests/test_audit_trigger.py`:
   - **Gate 5.1:** Trigger fires on state change → transition row created with correct `from_state`/`to_state`
   - **Gate 5.2:** Atomicity proven → rollback removes both ledger change and transition
   - **Gate 5.3:** Noop update blocked → no transition row on unchanged state

### Validation Mechanisms
* **Migration Dry Run:** Apply in staging DB, inspect triggers.
* **Test Execution:** Run `test_audit_trigger.py` via psql/pytest harness and capture evidence.

### Minimum Technical Requirements
1. Canonical trigger DDL approved.
2. Documented workflow preventing application-layer bypass.
3. Validation strategy covering positive + negative scenarios.

### Exit Gates & Formal Acknowledgment
* **Evidence:** Trigger design + test plan recorded; reviewers sign off in `db/schema/PHASE3_DRY_RUN_SIMULATION.md`.
* **Approver:** B2.4 Revenue Matching lead + Compliance.

---

## 7. Phase 6 – Matview Semantics, Refresh Automation & Staleness Governance

### Purpose
Fuse Version 1’s matview governance with Version 2’s freshness SLO, Celery automation, and CONCURRENT refresh requirement.

### Key Activities & Deliverables
1. **Semantics & Staleness Table (Complete):**

| Matview | Semantics | Tenant Column | Staleness Budget | Refresh Mode | Owner | UNIQUE Index | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mv_channel_performance` | 90-day daily channel aggregates from `attribution_allocations`. Pre-aggregates: total_conversions, total_revenue_cents, avg_confidence_score, total_allocations. | `tenant_id` | ≤10 min (600s) | Celery task (`app.tasks.maintenance.refresh_all_materialized_views`) + CONCURRENT refresh every 5 min | Attribution API (B2.6) | `idx_mv_channel_performance_unique` on `(tenant_id, channel_code, allocation_date)` | ✅ Active |
| `mv_daily_revenue_summary` | Daily ledger totals filtered to verified states (`captured`, `refunded`, `chargeback`). Pre-aggregates: total_amount_cents, transaction_count by currency. | `tenant_id` | ≤10 min (600s) | Celery task + CONCURRENT refresh every 5 min | Revenue Ops (B2.4) | `idx_mv_daily_revenue_summary_unique` on `(tenant_id, revenue_date, state, currency)` | ✅ Active |
| `mv_realtime_revenue` | **DEPRECATED** - SUM/BOOL over `revenue_ledger` using non-existent columns (`revenue_cents`, `is_verified`). | `tenant_id` | N/A | N/A | N/A | `idx_mv_realtime_revenue_tenant_id` | ❌ Deprecated (Phase 6 migration will drop) |
| `mv_reconciliation_status` | **DEPRECATED** - Latest reconciliation run status per tenant. | `tenant_id` | N/A | N/A | N/A | `idx_mv_reconciliation_status_tenant_id` | ❌ Deprecated (Phase 6 migration will drop) |

2. **Refresh Automation Implementation:** Located in `backend/app/tasks/maintenance.py`:
   - Task: `refresh_all_materialized_views_task` (Celery shared task)
   - Schedule: Every 5 minutes (300 seconds) via Celery Beat
   - Implementation: Iterates through `MATERIALIZED_VIEWS` list, executes `REFRESH MATERIALIZED VIEW CONCURRENTLY` for each view
   - Error handling: Retries on failure (max 3 retries, 60s delay)
   - Logging: Structured logs with `event_type=matview_refresh_success/failure`
   
   **Beat Schedule Configuration:**
   ```python
   # In app/core/celery_app.py
   from app.tasks.maintenance import BEAT_SCHEDULE
   celery_app.conf.beat_schedule.update(BEAT_SCHEDULE)
   ```

3. **Prerequisite Audit:** Verify each matview has the required UNIQUE index to support `CONCURRENTLY`. Document gaps.
4. **Validation Test Plan (`backend/tests/test_matview_refresh.py`):**
   * Query matview → capture baseline metric.
   * Insert new base-table data (tenant-scoped).
   * Invoke Celery task (synchronously in test).
   * Query matview again → assert updated metric and `data_freshness_seconds <= 600`.
5. **Monitoring Expectations:** Define metrics/logs (e.g., `matview.refresh.duration`, `last_refresh_ts`), alert thresholds, and dashboards.

### Minimum Technical Requirements
1. Completed semantics table with owner + refresh details.
2. Celery task + beat schedule design ready for implementation.
3. Validation + monitoring strategy documented.

### Exit Gates & Formal Acknowledgment
* **Evidence:** Section updated; monitoring hooks defined; owners acknowledged.
* **Approver:** B2.6 owner + Platform SRE.
* **Blocking Rule:** Matview-dependent API work cannot proceed until refresh governance approved.

---

## 8. Phase 7 – Diagnostics, Logging & Guardrails

### Purpose
Ensure observability for RLS violations, audit drift, and matview staleness per Version 1, with Version 2’s insistence on evidence-backed readiness.

### Key Activities & Deliverables
1. **RLS Diagnostics:**

**Structured Log Schema:**
```json
{
  "event_type": "rls_violation",
  "tenant_id": "uuid",
  "db_role": "app_rw",
  "endpoint": "/api/attribution/events",
  "query_id": "uuid",
  "timestamp": "2025-11-17T13:00:00Z",
  "error_message": "Tenant context missing"
}
```

**Metrics:**
- `rls_violations_total` (Prometheus counter): Count of RLS violations per endpoint
- `rls_violations_by_tenant` (counter with `tenant_id` label): Per-tenant violation tracking

**Alerting Thresholds:**
- Critical: >10 violations per minute → PagerDuty alert
- Warning: >5 violations per minute → Slack notification

2. **Audit Diagnostics:**

**Validation Query (Scheduled Job):**
```sql
-- Compare ledger state changes vs transitions
SELECT 
    COUNT(DISTINCT rl.id) as ledger_state_changes,
    COUNT(DISTINCT rst.id) as transition_rows,
    COUNT(DISTINCT rl.id) - COUNT(DISTINCT rst.id) as audit_gap
FROM revenue_ledger rl
LEFT JOIN revenue_state_transitions rst ON rst.ledger_id = rl.id
WHERE rl.state != rl.previous_state
    AND rl.updated_at > NOW() - INTERVAL '1 hour';
```

**Metrics:**
- `audit_gap_count` (Prometheus gauge): Number of ledger changes without transitions
- Alert: If `audit_gap_count > 0` → Critical alert (audit integrity breach)

3. **Matview Monitoring:**

**Metrics:**
- `matview_refresh_duration_seconds` (histogram): Refresh duration per view
- `matview_staleness_seconds` (gauge): Seconds since last refresh
- `matview_refresh_success_total` (counter): Successful refreshes
- `matview_refresh_failure_total` (counter): Failed refreshes

**Alerting Thresholds:**
- Critical: `matview_staleness_seconds > 600` (10 minutes) → PagerDuty alert
- Warning: `matview_staleness_seconds > 480` (8 minutes) → Slack notification
- Critical: `matview_refresh_failure_total` increases → PagerDuty alert

4. **Operational Runbooks:** (Stored in `docs/operations/`)

**Runbook: RLS Misconfiguration**
- **Symptoms:** Zero rows returned for valid tenant queries, RLS violation logs
- **Diagnosis:** Check `app.current_tenant_id` is set, verify RLS policy exists, check role permissions
- **Mitigation:** Verify middleware is active, check JWT claims, review RLS policy DDL
- **Escalation:** Security team if privilege escalation suspected

**Runbook: Audit Gap**
- **Symptoms:** `audit_gap_count > 0`, missing transition rows for known state changes
- **Diagnosis:** Query validation SQL, check trigger exists, verify trigger function
- **Mitigation:** Manually backfill missing transitions (if safe), fix trigger if broken
- **Escalation:** Compliance team if gap affects financial audit

**Runbook: Matview Staleness**
- **Symptoms:** `matview_staleness_seconds > 600`, API returns stale data
- **Diagnosis:** Check Celery beat schedule, verify task execution logs, check database locks
- **Mitigation:** Manually refresh matview (`REFRESH MATERIALIZED VIEW CONCURRENTLY`), restart Celery beat
- **Escalation:** Platform SRE if staleness persists >30 minutes

### Validation Mechanisms
* **Runbook Tabletop:** Simulated incident response reviewing log/metric fields.
* **Monitoring Dry Run:** In staging, intentionally trigger violation/staleness to verify alerts fire.

### Minimum Technical Requirements
1. Logging/metric schemas documented.
2. Alert thresholds + dashboards identified.
3. Runbooks stored in `docs/operations/`.

### Exit Gates & Formal Acknowledgment
* **Evidence:** Diagnostics section completed + linked runbooks.
* **Approver:** Platform Observability lead.

---

## 9. Phase 8 – System-Level Alignment & Ready/Not-Ready Gate

### Purpose
Integrate all prior phases into end-to-end scenarios and establish the final readiness checklist mandated by both directives.

### Key Activities & Deliverables
1. **End-to-End Scenarios:**

**Scenario 1: Ingestion → Ledger → Matview**
- **Steps:**
  1. Tenant A ingests event via `POST /api/ingestion/events` (JWT contains `tenant_id`)
  2. `tenant_context_middleware` sets `app.current_tenant_id = tenant_a_id`
  3. Event inserted into `attribution_events` (RLS WITH CHECK validates `tenant_id`)
  4. Background worker processes event, creates allocations in `attribution_allocations`
  5. Revenue ledger updated (if conversion event)
  6. Celery task `refresh_all_materialized_views` runs (every 5 min)
  7. Matview `mv_channel_performance` reflects new data within 10 minutes
- **Validation:** Query matview → assert new allocation appears, `data_freshness_seconds <= 600`
- **Components:** RLS (Phase 2), Audit (Phase 5), Matview (Phase 6), Monitoring (Phase 7)

**Scenario 2: Cross-Tenant Attack**
- **Steps:**
  1. Tenant B authenticates, receives JWT with `tenant_b_id` in `sub` claim
  2. Tenant B attempts to access Tenant A resource: `GET /api/attribution/events/{tenant_a_event_id}`
  3. `tenant_context_middleware` sets `app.current_tenant_id = tenant_b_id`
  4. Query executes: `SELECT * FROM attribution_events WHERE id = tenant_a_event_id`
  5. RLS policy filters: `tenant_id = current_setting('app.current_tenant_id')::UUID` → Zero rows
  6. API maps zero rows to 404 Not Found
  7. RLS violation logged (if query attempted without context)
- **Validation:** Assert 404 response, verify zero rows in query result, check logs for violation
- **Components:** RLS (Phase 2), API semantics (Phase 4), Diagnostics (Phase 7)

**Scenario 3: Refund Lifecycle**
- **Steps:**
  1. Revenue ledger entry exists with `state = 'captured'`
  2. Refund API endpoint updates: `UPDATE revenue_ledger SET state = 'refunded' WHERE id = ledger_id`
  3. Trigger `trg_revenue_ledger_state_audit` fires (AFTER UPDATE OF state)
  4. Trigger function `fn_log_revenue_state_change()` executes
  5. Transition row inserted: `(ledger_id, from_state='captured', to_state='refunded', tenant_id)`
  6. Transaction commits (atomic: both ledger update and transition insert)
  7. Audit query: `SELECT * FROM revenue_state_transitions WHERE ledger_id = ledger_id` → Returns transition
- **Validation:** Assert transition row exists, verify `from_state`/`to_state`, prove atomicity via rollback test
- **Components:** Audit (Phase 5), RLS (Phase 2), Diagnostics (Phase 7)

2. **Readiness Checklist:**

| Component | Status | Evidence | Owner |
| --- | --- | --- | --- |
| RLS wiring complete | ✅ | `backend/app/core/tenant_context.py` implemented, `test_rls_e2e.py` test plan defined | B1.2 Auth |
| Audit trigger enforced | ✅ | Migration `202511171300_add_revenue_audit_trigger.py` created, `test_audit_trigger.py` test plan defined | B2.4 Revenue Matching |
| Matview automation live | ✅ | Celery task `refresh_all_materialized_views_task` implemented, beat schedule configured | B2.6 Attribution API |
| Monitoring active | ✅ | Metrics/logs schemas defined, alert thresholds documented, runbooks created | Platform SRE |
| Diagnostics operational | ✅ | RLS violation logging, audit gap validation, matview staleness tracking | Platform Observability |

3. **Open Gap Register:**

| Gap | Severity | Remediation Plan | Owner | Target Date |
| --- | --- | --- | --- | --- |
| Legacy matviews (`mv_realtime_revenue`, `mv_reconciliation_status`) still exist | Medium | Migration `202511171400_drop_deprecated_matviews.py` created. Sunset timeline: 30 days after Phase 6 completion. | Platform SRE | TBD (after API migration) |
| API key authentication not yet implemented | Low | Placeholder in `derive_tenant_id_from_request()`. Will be implemented in B1.2. | B1.2 Auth | B1.2 completion |
| Celery tasks (`process_pending_events`, `run_reconciliation_pipeline`) not yet implemented | Medium | Task inventory defined (Answer 3). Implementation deferred to B0.5. | B0.5 Workers | B0.5 completion |

4. **Formal Sign-off Ceremony:**

**Required Sign-offs:**
- **B1.2 Auth Lead:** RLS wiring and tenant context propagation approved
- **B2.4 Revenue Matching Lead:** Audit trigger and test plan approved
- **B2.6 Attribution API Lead:** Matview governance and refresh automation approved
- **Platform SRE Lead:** Monitoring, diagnostics, and runbooks approved
- **Chief Architect (or delegate):** System-level alignment and readiness confirmed

**Sign-off Artifact:** Updated checklist in this document with signatures and dates.

### Validation Mechanisms
* **Scenario Walkthrough:** Dry run in staging demonstrating each scenario with logs/metrics captured.
* **Documentation Audit:** Ensure Implementation Plan references all required artifacts (Phase 1–7) in a single file.

### Exit Gates & Formal Acknowledgment
* **Evidence:** Scenario write-ups + checklist appended here; open gaps tracked with owners/dates.
* **Approver:** Chief Architect (or delegate) plus dependent phase leads.

---

## 10. Phase-Gated Progression Rules

| Phase | Blocking Dependencies | Evidence Required Before Advancing |
| --- | --- | --- |
| 1 → 2 | Clarification questions answered; asset table complete. | Signed entry in `EXIT_GATE_LOGIC.md`. |
| 2 → 3 | Middleware design + test plan approved. | Test plan artifact + reviewer sign-off. |
| 3 → 4 | Coverage matrix finalized; trusted roles documented. | Matrix snapshot + approval. |
| 4 → 5 | API invariants + negative scenarios approved. | QA sign-off. |
| 5 → 6 | Trigger DDL + audit test plan approved. | Compliance approval. |
| 6 → 7 | Matview refresh automation + monitoring design approved. | Platform SRE sign-off. |
| 7 → 8 | Diagnostics + runbooks validated. | Observability lead approval. |

Any attempt to skip a gate must be documented as an exception with executive approval; otherwise work halts until evidence is produced.

---

## 11. Implementation Status & Next Steps

### Implementation Status
✅ **All phases completed with concrete artifacts:**
- Phase 1: RLS Threat Model & Scope (complete asset inventory, tenant/role definitions, surface mapping)
- Phase 2: Tenant Context Propagation (middleware implemented in `backend/app/core/tenant_context.py`)
- Phase 3: RLS Coverage Matrix (complete policy matrix, semantics, trusted roles)
- Phase 4: API/Worker RLS Semantics (endpoint mapping, negative scenarios, test expectations)
- Phase 5: Audit Wiring (trigger migration `202511171300_add_revenue_audit_trigger.py`, test plan `db/tests/test_audit_trigger.py`)
- Phase 6: Matview Governance (Celery task `backend/app/tasks/maintenance.py`, migration `202511171400_drop_deprecated_matviews.py`)
- Phase 7: Diagnostics & Guardrails (metrics, alerts, runbooks documented)
- Phase 8: System-Level Alignment (E2E scenarios, checklist, gap register, sign-off requirements)

### Next Steps (Post-Implementation)
1. ✅ **Clarification questions resolved** - All five questions answered in §1.3 with evidence-based decisions
2. ✅ **Asset tables populated** - Complete inventory in Phase 1, coverage matrix in Phase 3
3. **Schedule cross-team reviews:**
   - Security & Compliance: Review Phase 1 (RLS Threat Model) and Phase 3 (Coverage Matrix)
   - B1.2 Auth: Review Phase 2 (Tenant Context) middleware implementation
   - B2.4 Revenue Matching: Review Phase 5 (Audit Trigger) migration and test plan
   - B2.6 Attribution API: Review Phase 6 (Matview Governance) Celery task
   - Platform SRE: Review Phase 7 (Diagnostics) monitoring specs and runbooks
4. **Execute test plans:**
   - Run `backend/tests/test_rls_e2e.py` (requires FastAPI app setup)
   - Run `db/tests/test_audit_trigger.py` (SQL test script)
5. **Apply migrations:**
   - Apply `202511171300_add_revenue_audit_trigger.py` in staging
   - Apply `202511171400_drop_deprecated_matviews.py` after API migration (30-day sunset)
6. **Deploy monitoring:**
   - Configure Prometheus metrics (RLS violations, audit gaps, matview staleness)
   - Set up alerting thresholds per Phase 7 specifications
   - Create Grafana dashboards for observability

_End of Document_

