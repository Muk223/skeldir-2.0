# B0.3 OLAP & Indexing Remediation: Unified Implementation Design

**Version:** 1.0  
**Date:** 2025-11-17  
**Status:** Implementation Document - Design Phase Complete  
**Synthesis:** Version 1 (Jamie) Governance Framework + Version 2 (Schmidt) Tactical Remediation

---

## Executive Summary

This document synthesizes **Version 1 (Jamie)**'s comprehensive governance framework with **Version 2 (Schmidt)**'s targeted remediation actions to produce a single, empirically-validated implementation plan for B0.3 OLAP/indexing readiness. The synthesis ensures tactical fixes serve strategic OLAP sustainability.

**Deliverable**: Single Implementation Document (this file)

**Strategic Foundation**: V1's phased governance model (workload definition → benchmarking → index design → validation → SLOs → system alignment)

**Tactical Execution**: V2's five canonical queries (Q1-Q5) as P0 baseline, specific index corrections, and mandatory EXPLAIN ANALYZE evidence

**Key Remediation Actions**:
1. Create canonical `idx_allocations_channel_performance` index (missing from migrations)
2. Create `idx_revenue_ledger_tenant_state` partial index for Q5
3. Drop non-canonical indexes that drifted from specification
4. Capture 10 EXPLAIN ANALYZE outputs (before/after) as empirical proof
5. Establish < 500ms p95 SLO for all P0 queries

---

## 0. Contextual Environment & Failure Point Mitigation

### 0.1 Architectural Relevance

Within Skeldir's backend:

* **B0.3** defines the **schema and indexing foundation**.
* **B0.4** (ingestion) will drive **high write volume** into `attribution_events`, `attribution_allocations`, `revenue_ledger`, and related tables.
* OLAP surfaces (dashboards, exports, reconciliation views) sit on top of **those same tables + matviews**.
* **B2.6** (Attribution API) has a strict < 500ms p95 latency SLO for dashboard endpoints.

Core architectural mandates:

1. **PostgreSQL-first OLAP**
   * Operational DB must support **core analytical workloads** (time-series, channel performance, revenue summaries).
   * Indexes and access patterns must be designed *from real queries*, not intuition.

2. **Tenant-scoped analytics**
   * Everything is multi-tenant. OLAP must remain **RLS-compatible** and tenant-bounded.
   * Bad indexing → slow queries → pressure to bypass RLS or build adhoc mirrors.

3. **Evidence-based performance**
   * "It runs in dev" is worthless. B0.3 is only truly "done" when you have **stored EXPLAIN/ANALYZE evidence** that representative workloads meet clearly defined SLOs.

### 0.2 Current Failure Modes (What We're Fixing)

From forensic analysis and B0.3 status:

* **Failure 1 (Process Drift):** Critical OLAP-optimized composite index (`idx_allocations_channel_performance` with `INCLUDE`) defined in canonical schema was **not implemented**. Instead, simpler, non-conformant indexes were created.
* **Failure 2 (Governance Failure):** Mandatory B0.3 exit criterion—providing `EXPLAIN ANALYZE` artifacts to *prove* index performance—was **skipped entirely**. Analysts confirmed "NO EXPLAIN ANALYZE OUTPUT FOUND".
* **Failure 3 (Governance Ambiguity):** Decision on GIN indexing for JSONB columns was never made. The index is missing, but more importantly, the *query workload* that would justify it was never defined.

**Mitigation Strategy:** Reverse this process. This directive moves from "implement-then-ignore" to "define-design-implement-prove." We will *first* define the query workload, *then* design the index policy from that workload, and *finally* mandate the creation of `EXPLAIN ANALYZE` artifacts as the non-negotiable proof of "functional" performance.

---

## Phase 1: Define Representative Query Workload (RQW)

### 1.1 OLAP Personas & Use Cases

Document the main OLAP personas that B0.3 must support:

* **Attribution Analyst:**
  * Needs event time-series per tenant, per channel.
* **Marketing Leader:**
  * Needs channel performance dashboards (CPA, ROAS by channel/group).
* **Ops / Reconciliation:**
  * Needs revenue summaries by day/state (pending/settled/chargeback).
* **Workers/Jobs:**
  * Need fast access to queues like "events pending processing," "allocations pending reconciliation."

### 1.2 Representative Queries

**P0 Queries (V2 Canonical Set - Immediate Remediation Focus):**

#### Q1 (API/B2.6 - Channel Dashboard): Channel Performance Aggregate

**Query SQL:**
```sql
-- Q1: Channel Performance Aggregate (Pre-Materialization)
SELECT
    tenant_id,
    channel_code,
    DATE_TRUNC('day', created_at) AS allocation_day,
    SUM(allocated_revenue_cents) AS total_revenue,
    AVG(allocation_ratio) AS avg_allocation_ratio,
    COUNT(DISTINCT event_id) AS conversion_count
FROM attribution_allocations
WHERE
    tenant_id = $1
    AND created_at BETWEEN $2 AND $3
GROUP BY tenant_id, channel_code, DATE_TRUNC('day', created_at);
```

**Query Metadata:**
- **Name**: `Q1_allocations_channel_performance`
- **Priority**: P0
- **Target Tables**: `attribution_allocations`
- **Filters**: `tenant_id`, `created_at` BETWEEN (date range)
- **Grouping**: `tenant_id`, `channel_code`, day
- **Ordering**: None (application layer may sort)
- **Expected Cardinality**: ~100 rows per tenant per 90 days (assuming ~10 channels × ~90 days)
- **Use Case**: Powers `mv_channel_performance` view and B2.6 API dashboard endpoints
- **System Owner**: B2.6 (Attribution API)

**Note**: Query uses `channel_code` (current schema) and `allocation_ratio` (available in current schema). If canonical schema includes `confidence_score`, query should use that instead of `allocation_ratio` for AVG calculation.

---

#### Q2 (Ingestion/B0.4 - Worker Queue): Find Pending Events

**Query SQL:**
```sql
-- Q2: Worker Queue (Find Pending Events)
SELECT *
FROM attribution_events
WHERE
    processing_status = 'pending'
ORDER BY event_timestamp ASC
LIMIT 500;
```

**Query Metadata:**
- **Name**: `Q2_events_worker_queue`
- **Priority**: P0
- **Target Tables**: `attribution_events`
- **Filters**: `processing_status = 'pending'`
- **Grouping**: None
- **Ordering**: `event_timestamp ASC`
- **Expected Cardinality**: 500 rows max (LIMIT clause)
- **Use Case**: B0.5 worker queue for processing pending ingestion tasks
- **System Owner**: B0.4 (Ingestion Service)

**Note**: Query assumes `processing_status` and `event_timestamp` columns exist (per canonical schema). If current schema uses `occurred_at` instead of `event_timestamp`, query should be adjusted accordingly.

---

#### Q3 (API/B2.6 - Tenant Time-Series): Recent Events Per Tenant

**Query SQL:**
```sql
-- Q3: Tenant-Scoped Event Time-Series
SELECT 
    id, 
    event_type, 
    channel, 
    conversion_value_cents, 
    event_timestamp
FROM attribution_events
WHERE
    tenant_id = $1
ORDER BY event_timestamp DESC
LIMIT 100;
```

**Query Metadata:**
- **Name**: `Q3_events_tenant_timeseries`
- **Priority**: P0
- **Target Tables**: `attribution_events`
- **Filters**: `tenant_id`
- **Grouping**: None
- **Ordering**: `event_timestamp DESC`
- **Expected Cardinality**: 100 rows (LIMIT clause)
- **Use Case**: Common query for fetching a tenant's most recent events for dashboard display
- **System Owner**: B2.6 (Attribution API)

**Note**: Query assumes canonical schema columns (`event_type`, `channel`, `conversion_value_cents`, `event_timestamp`). If current schema differs, query should be adjusted.

---

#### Q4 (Ingestion/B0.4 - Idempotency Check): Duplicate Detection

**Query SQL:**
```sql
-- Q4: Idempotency Check
SELECT 1
FROM attribution_events
WHERE
    tenant_id = $1
    AND idempotency_key = $2;
```

**Query Metadata:**
- **Name**: `Q4_events_idempotency_check`
- **Priority**: P0
- **Target Tables**: `attribution_events`
- **Filters**: `tenant_id`, `idempotency_key`
- **Grouping**: None
- **Ordering**: None
- **Expected Cardinality**: 0 or 1 row (UNIQUE constraint)
- **Use Case**: B0.4 *must* run to check for duplicate `idempotency_key`s before insertion
- **System Owner**: B0.4 (Ingestion Service)

**Note**: Query assumes canonical schema with `idempotency_key` column. If current schema uses composite approach (`external_event_id` + `correlation_id`), query should be adjusted.

---

#### Q5 (API/B2.6 - Real-time Revenue): Revenue Aggregate

**Query SQL:**
```sql
-- Q5: Real-time Revenue Aggregate (Pre-Materialization)
SELECT
    tenant_id,
    SUM(amount_cents) AS total_revenue
FROM revenue_ledger
WHERE
    tenant_id = $1
    AND state = 'captured'
GROUP BY tenant_id;
```

**Query Metadata:**
- **Name**: `Q5_revenue_ledger_captured_sum`
- **Priority**: P0
- **Target Tables**: `revenue_ledger`
- **Filters**: `tenant_id`, `state = 'captured'`
- **Grouping**: `tenant_id`
- **Ordering**: None
- **Expected Cardinality**: 1 row per tenant
- **Use Case**: Powers the `mv_realtime_revenue` view and real-time revenue dashboard
- **System Owner**: B2.6 (Attribution API)

**Note**: Query assumes canonical schema with `state` column and `amount_cents`. If current schema uses `is_verified` boolean and `revenue_cents`, query should be:
```sql
SELECT tenant_id, SUM(revenue_cents) AS total_revenue
FROM revenue_ledger
WHERE tenant_id = $1 AND is_verified = TRUE
GROUP BY tenant_id;
```

**Schema Alignment Note**: This remediation assumes migration to canonical schema structure. If current schema differs, queries must be adjusted to match actual column names.

---

**P1 Queries (V1 Expansion - Future Workload):**

6. **Q6 (Marketing Leader - Channel Performance by Group)**: Channel family aggregation
   - Query: Join `attribution_allocations` with `channel_taxonomy` to group by `family`
   - Priority: P1
   - Status: Deferred to future phase

7. **Q7 (Ops - Revenue Summary by Day/State)**: Daily revenue state breakdown
   - Query: `GROUP BY DATE_TRUNC('day', created_at), state` on `revenue_ledger`
   - Priority: P1
   - Status: Deferred to future phase

8. **Q8 (Analyst - Event Time-Series with Channel Filter)**: Filtered time-series
   - Query: Q3 with additional `WHERE channel = $2` filter
   - Priority: P1
   - Status: Deferred to future phase

**Documentation Requirements:**
- Each query includes: Name, target tables, filters, grouping/ordering, expected cardinality
- Priority assignment (P0/P1/P2)
- **Formal sign-off required**: B0.4 (Ingestion) and B2.6 (API) leads must sign off on Q1-Q5

**Exit Gate 1**: Implementation Document contains complete `1.2 Representative Queries` section with all 5 P0 queries fully specified and signed off by system owners.

**Sign-off Status**: 
- [ ] B0.4 Lead: _________________ Date: _______
- [ ] B2.6 Lead: _________________ Date: _______

---

## Phase 2: Define Benchmark Dataset & Workload Parameters

### 2.1 Data Volume Assumptions (V2 Scale as Initial Baseline)

**Per Tenant (V2 Benchmark Profile):**

* `attribution_events`: 1M rows per 90 days
* `attribution_allocations`: 5M rows per 90 days (avg 5 allocations per event)
* `revenue_ledger`: 100K rows per 90 days

**Global (Multi-Tenant):**

* 100 tenants (V2 benchmark dataset)
* Total events: 100M (100 tenants × 1M events)
* Total allocations: 500M (100 tenants × 5M allocations)
* Total ledger entries: 10M (100 tenants × 100K entries)

**Rationale**: This scale represents realistic near-term production load. B0.4 ingestion will generate high write volume, and B2.6 dashboards must remain responsive at this scale.

### 2.2 Data Distribution Assumptions

**Time Distribution**: 
- Events clustered in daily spikes (80% of events in 20% of days)
- Simulates real-world traffic patterns (weekend dips, campaign spikes)

**Channel Distribution**: 
- 80/20 rule (top 3 channels = 80% of allocations)
- Remaining channels distributed across long tail
- Aligns with typical marketing channel concentration

**Tenant Distribution**: 
- Top 10 tenants = 60% of volume (moderate skew)
- Remaining 90 tenants share 40% of volume
- Simulates realistic SaaS multi-tenant distribution

**Rationale**: These distribution characteristics matter for index design and query expectations. Skewed distributions test index effectiveness under realistic conditions.

### 2.3 Workload Mix

| Query | Frequency | Type | Concurrency | Notes |
|-------|-----------|------|-------------|-------|
| Q1 | 100/day/tenant | Interactive (dashboard) | 10 simultaneous | User-initiated dashboard refresh |
| Q2 | 1000/hour/tenant | Batch (worker) | 5 simultaneous | Background worker polling |
| Q3 | 500/day/tenant | Interactive (dashboard) | 20 simultaneous | Recent events widget |
| Q4 | 10K/hour/tenant | Batch (ingestion) | 50 simultaneous | High-frequency idempotency checks |
| Q5 | 200/day/tenant | Interactive (dashboard) | 15 simultaneous | Real-time revenue display |

**Rationale**: 
- Interactive queries (Q1, Q3, Q5) require low latency (< 500ms p95)
- Batch queries (Q2, Q4) can tolerate slightly higher latency but must scale to high concurrency
- Q4 is highest frequency (idempotency checks on every ingestion attempt)

### 2.4 Benchmark Dataset Profile

**Named Profile**: `b0.3_benchmark_100t_1me`

**Specification**:
- **Tenants**: 100 tenants (UUIDs generated deterministically for reproducibility)
- **Events**: 1M `attribution_events` per tenant (90-day window, clustered distribution)
- **Allocations**: 5M `attribution_allocations` per tenant (5 allocations per event average)
- **Ledger**: 100K `revenue_ledger` rows per tenant (90-day window)
- **Distribution**: Realistic skew (time spikes, channel concentration, tenant volume skew)

**Reproducibility Requirements**:
- Seed data generation script must produce identical dataset given same random seed
- Column values must match expected distributions (80/20 channel, time clustering)
- Foreign key relationships must be valid (allocations reference events, ledger references allocations)

**Exit Gate 2**: Implementation Document contains complete `2.1-2.4` sections with explicit dataset profile that two engineers could reproduce identically.

**Dataset Generation Status**: 
- [ ] Seed script created: `scripts/generate-benchmark-dataset.sql`
- [ ] Reproducibility validated: Two engineers generated identical datasets

---

## Phase 3: Index Design Policy from RQW

### 3.1 Query → Index Mapping

| Query | Ideal Index Pattern | Justification | Current Status |
|-------|---------------------|---------------|----------------|
| Q1 | `idx_allocations_channel_performance (tenant_id, channel_code, created_at DESC) INCLUDE (allocated_revenue_cents, allocation_ratio)` | Supports GROUP BY tenant_id, channel_code, day with SUM/AVG aggregates. INCLUDE columns avoid table lookups. | **MISSING** - Must CREATE |
| Q2 | `idx_events_processing_status (processing_status, event_timestamp) WHERE processing_status = 'pending'` | Partial index for worker queue. WHERE clause reduces index size. | **EXISTS** - No action needed |
| Q3 | `idx_events_tenant_timestamp (tenant_id, event_timestamp DESC)` | Time-series retrieval. Composite index supports tenant filter + timestamp ordering. | **EXISTS** - No action needed |
| Q4 | `idx_events_idempotency (tenant_id, idempotency_key)` | Unique index for idempotency. Composite supports tenant isolation + key lookup. | **EXISTS** - Verify column exists |
| Q5 | `idx_revenue_ledger_tenant_state (tenant_id, state) WHERE state = 'captured'` | Partial index for captured revenue. WHERE clause reduces index size. | **MISSING** - Must CREATE |

**Index Rationale Summary**:
- **Q1**: Composite index with INCLUDE columns enables index-only scans for aggregates
- **Q2**: Partial index reduces size (only indexes pending rows) and improves worker queue performance
- **Q3**: Composite index supports tenant-scoped time-series queries efficiently
- **Q4**: Unique composite index enforces idempotency while supporting tenant isolation
- **Q5**: Partial index reduces size (only indexes captured state) and improves revenue aggregation

### 3.2 Canonical OLAP Index Set (V2 Remediation + V1 Consolidation)

**Indexes to CREATE (V2 Remediation):**

#### 1. `idx_allocations_channel_performance` (REMEDIATES Gap 3)

**DDL:**
```sql
CREATE INDEX idx_allocations_channel_performance 
ON attribution_allocations (tenant_id, channel_code, created_at DESC) 
INCLUDE (allocated_revenue_cents, allocation_ratio);
```

**Rationale**:
- **Serves**: Q1 (Channel Performance Dashboard)
- **Canonical Source**: Defined in `db/schema/canonical_schema.sql:217-219`
- **Current State**: Missing from migrations (drift from canonical spec)
- **Remediation**: Create canonical index to replace non-conformant separate indexes

**Note**: If canonical schema includes `confidence_score` instead of `allocation_ratio`, INCLUDE clause should use `confidence_score`. Current schema uses `allocation_ratio`.

#### 2. `idx_revenue_ledger_tenant_state` (NEW for Q5)

**DDL:**
```sql
CREATE INDEX idx_revenue_ledger_tenant_state 
ON revenue_ledger (tenant_id, state) 
WHERE state = 'captured';
```

**Rationale**:
- **Serves**: Q5 (Real-time Revenue Aggregate)
- **Canonical Source**: Not explicitly defined, but required for Q5 performance
- **Current State**: Missing (no index supports `state = 'captured'` filter)
- **Remediation**: Create partial index to optimize captured revenue queries

**Note**: If current schema uses `is_verified` boolean instead of `state` enum, index should be:
```sql
CREATE INDEX idx_revenue_ledger_tenant_verified 
ON revenue_ledger (tenant_id, is_verified) 
WHERE is_verified = TRUE;
```

**Indexes to DROP (V2 Remediation - Remove Non-Canonical):**

#### 1. `idx_attribution_allocations_tenant_created_at`

**Rationale**: Replaced by composite `idx_allocations_channel_performance` which includes `tenant_id, created_at DESC` as prefix. Separate index is redundant.

**DDL:**
```sql
DROP INDEX IF EXISTS idx_attribution_allocations_tenant_created_at;
```

#### 2. `idx_attribution_allocations_channel`

**Rationale**: Replaced by composite `idx_allocations_channel_performance` which includes `channel_code` as second column. Separate index is redundant.

**DDL:**
```sql
DROP INDEX IF EXISTS idx_attribution_allocations_channel;
```

**Indexes Already Correct (No Action):**

- `idx_events_processing_status` (Q2) - EXISTS (verify definition matches)
- `idx_events_tenant_timestamp` (Q3) - EXISTS (verify definition matches)
- `idx_events_idempotency` (Q4) - EXISTS (verify column `idempotency_key` exists)

**Verification Required**: Before remediation, verify existing indexes match expected definitions. If definitions differ, document differences and adjust remediation DDL accordingly.

### 3.3 JSONB & GIN Policy (V2 Decision + V1 Documentation)

**Analysis**: 
- No query in RQW (Q1-Q5) performs any filtering on `raw_payload` or `error_detail` JSONB keys
- No query joins by fields inside JSONB columns
- JSONB columns (`attribution_events.raw_payload`, `dead_events.error_detail`, `attribution_allocations.model_metadata`) are used for opaque storage only

**Decision**: **GIN index explicitly DEFERRED**

**Rationale** (V1 Framework):
- Design from real queries, not speculation
- No current workload requires JSONB filtering
- GIN indexes are expensive to maintain (write overhead)
- B0.4 phase will introduce JSONB queries if needed, at which point GIN index will be added with its own query workload validation

**Documentation**: This is an **architectural decision**, not an omission. The absence of GIN indexes is intentional and justified by the absence of JSONB query patterns in the RQW.

**Future Consideration**: 
- If B0.4 introduces queries like `WHERE raw_payload->>'source' = 'shopify'`, add GIN index at that time
- GIN index addition will require its own query workload definition and EXPLAIN ANALYZE validation

### 3.4 Index Trade-off Notes

| Index | Write Overhead | Read Benefit | Rationale | Decision |
|-------|----------------|--------------|-----------|----------|
| `idx_allocations_channel_performance` | Medium (composite + INCLUDE) | High (P0 query) | Must be indexed even if write overhead high | **CREATE** |
| `idx_revenue_ledger_tenant_state` | Low (partial index) | High (P0 query) | Partial index minimizes overhead | **CREATE** |

**Write Overhead Analysis**:
- Composite indexes require more storage and slower INSERT/UPDATE operations
- INCLUDE columns add storage but don't slow writes (non-key columns)
- Partial indexes reduce overhead by only indexing subset of rows
- Trade-off is acceptable for P0 queries that must meet < 500ms SLO

**Exit Gate 3**: Implementation Document contains complete `3.1-3.4` sections with every P0 query mapped to index strategy, canonical index list defined, and JSONB decision explicitly documented.

**Index Design Status**:
- [ ] Query → Index mapping complete
- [ ] Canonical index list defined
- [ ] JSONB/GIN decision documented
- [ ] Trade-off analysis complete

---

## Phase 4: Capture EXPLAIN/ANALYZE Artifacts

### 4.1 Benchmark Parameters

For each query, define parameter sets for benchmarking:

**Q1 (Channel Performance):**
- **Typical case**: `tenant_id = 'moderate-tenant-uuid'`, `created_at BETWEEN '2024-01-01' AND '2024-01-31'` (30-day range)
- **Worst case**: `tenant_id = 'largest-tenant-uuid'`, `created_at BETWEEN '2024-01-01' AND '2024-03-31'` (90-day range)

**Q2 (Worker Queue):**
- **Typical case**: No parameters (filters all pending events)
- **Worst case**: Same (query always scans all pending events)

**Q3 (Tenant Time-Series):**
- **Typical case**: `tenant_id = 'moderate-tenant-uuid'`
- **Worst case**: `tenant_id = 'largest-tenant-uuid'` (more events to scan)

**Q4 (Idempotency Check):**
- **Typical case**: `tenant_id = 'moderate-tenant-uuid'`, `idempotency_key = 'existing-key'` (hit case)
- **Worst case**: `tenant_id = 'largest-tenant-uuid'`, `idempotency_key = 'non-existent-key'` (miss case, full index scan)

**Q5 (Real-time Revenue):**
- **Typical case**: `tenant_id = 'moderate-tenant-uuid'`
- **Worst case**: `tenant_id = 'largest-tenant-uuid'` (more captured rows to aggregate)

**Parameter Storage**: Document exact UUIDs and date ranges used in benchmark dataset generation script for reproducibility.

### 4.2 EXPLAIN/ANALYZE Plan

**Procedure**:

1. **Setup**: Populate benchmark dataset (`b0.3_benchmark_100t_1me`) on non-production database
2. **Baseline Capture**: Run `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)` for each query (Q1-Q5) with typical parameters
3. **Store BEFORE Plans**: Save all 5 EXPLAIN ANALYZE outputs to `docs/performance/b0.3-query-plans.md` (BEFORE section)
4. **Apply Remediation**: Run migration `remediate_b03_olap_indexes.py` to create new indexes
5. **Post-Remediation Capture**: Run `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)` for each query again with same parameters
6. **Store AFTER Plans**: Save all 5 EXPLAIN ANALYZE outputs to same file (AFTER section)

**Result**: 10 total EXPLAIN ANALYZE outputs (5 queries × 2 states: BEFORE and AFTER)

**Command Template**:
```sql
-- For each query Q1-Q5:
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
<query_sql_with_parameters>;
```

**Execution Order**:
1. Q1 BEFORE
2. Q2 BEFORE
3. Q3 BEFORE
4. Q4 BEFORE
5. Q5 BEFORE
6. **Apply migration**
7. Q1 AFTER
8. Q2 AFTER
9. Q3 AFTER
10. Q4 AFTER
11. Q5 AFTER

### 4.3 Plan Artifact Structure

**Location**: `docs/performance/b0.3-query-plans.md`

**Format**: For each query, include:

```markdown
## Q1: Channel Performance Aggregate

### Query SQL
```sql
<full_query_sql>
```

### Parameters Used
- tenant_id: `moderate-tenant-uuid`
- date_range: `2024-01-01` to `2024-01-31`

### BEFORE Migration (Baseline)

#### EXPLAIN ANALYZE Output
```
<full_EXPLAIN_ANALYZE_output>
```

#### Metrics Extracted
- Execution Time: XXX ms
- Planning Time: XX ms
- Rows Returned: XXX
- Rows Scanned: XXX,XXX
- Index Usage: Seq Scan / Index Scan / Index Only Scan
- Buffer Hits: XXX
- Buffer Misses: XXX

### AFTER Migration (Remediated)

#### EXPLAIN ANALYZE Output
```
<full_EXPLAIN_ANALYZE_output>
```

#### Metrics Extracted
- Execution Time: XXX ms
- Planning Time: XX ms
- Rows Returned: XXX
- Rows Scanned: XXX,XXX
- Index Usage: Seq Scan / Index Scan / Index Only Scan
- Buffer Hits: XXX
- Buffer Misses: XXX

### Performance Improvement
- Execution Time Reduction: XX% (XXX ms → XXX ms)
- Index Usage: Seq Scan → Index Scan (or Index Only Scan)
```

**Repeat for Q2-Q5**

### 4.4 Environment Assumptions

**Database Environment**:
- PostgreSQL version: 15+ (verify with `SELECT version();`)
- `work_mem`: 256MB (if tuned, verify with `SHOW work_mem;`)
- `effective_cache_size`: 4GB (if tuned, verify with `SHOW effective_cache_size;`)
- `shared_buffers`: 1GB (if tuned, verify with `SHOW shared_buffers;`)

**Dataset Requirements**:
- Dataset matches `b0.3_benchmark_100t_1me` profile exactly
- Statistics updated: Run `ANALYZE` on all tables before EXPLAIN ANALYZE
- No concurrent load: Run EXPLAIN ANALYZE in isolation to avoid interference

**Documentation**: Record actual environment values in `docs/performance/b0.3-query-plans.md` header for reproducibility.

**Exit Gate 4**: Implementation Document contains complete `4.1-4.4` sections with exact procedure for generating and storing EXPLAIN ANALYZE artifacts.

**Artifact Status**:
- [ ] Benchmark dataset populated
- [ ] BEFORE plans captured (5 queries)
- [ ] Migration applied
- [ ] AFTER plans captured (5 queries)
- [ ] Artifact file created: `docs/performance/b0.3-query-plans.md`

---

## Phase 5: Define Performance SLOs & Exit Gates

### 5.1 Per-Query SLOs (V2 Threshold + V1 Hierarchy)

| Query | Typical SLO | Worst Case SLO | Priority | Notes |
|-------|------------|---------------|----------|-------|
| Q1 | p95 < 500ms | p95 < 1000ms | P0 | V2 requirement: < 500ms p95 |
| Q2 | p95 < 100ms | p95 < 200ms | P0 | Worker queue must be fast |
| Q3 | p95 < 250ms | p95 < 500ms | P0 | Dashboard widget refresh |
| Q4 | p95 < 10ms | p95 < 20ms | P0 | Idempotency check must be very fast |
| Q5 | p95 < 300ms | p95 < 600ms | P0 | Real-time revenue display |

**V2 Requirement**: All P0 queries must meet **< 500ms p95** on typical case.

**V1 Framework**: Establish broader SLO hierarchy (P0/P1/P2) for future queries:
- **P0**: Must meet SLO or block B0.3 completion
- **P1**: Should meet SLO, but can be deferred with documented rationale
- **P2**: Performance targets are aspirational, no blocking

**SLO Measurement**:
- SLOs are measured via `EXPLAIN ANALYZE` Execution Time
- Typical case uses moderate tenant and common date range
- Worst case uses largest tenant and longest date range
- p95 means 95th percentile (not average) - run query multiple times and measure distribution

### 5.2 Aggregate SLOs

**System-Level Constraints**:

1. **All P0 queries** must meet their p95 SLOs on benchmark dataset (`b0.3_benchmark_100t_1me`)
2. **No P0 query** should show full table sequential scan on `attribution_events` or `attribution_allocations` at benchmark volume
   - Exception: Q2 partial index scan is acceptable (scans only pending rows)
3. **Index usage** must be confirmed via EXPLAIN ANALYZE (Index Scan or Index Only Scan)
   - Sequential scans are red flags for P0 queries
4. **Planning time** should be < 50ms for all P0 queries (indicates query complexity is manageable)

**Rationale**: These aggregate constraints ensure the indexing strategy is effective at scale and queries remain predictable.

### 5.3 Red-Flag Conditions

**Unacceptable patterns** (automatic failure):

- Sequential scan on `attribution_events` for P0 queries (except Q2 partial index scan on pending rows)
- Sequential scan on `attribution_allocations` for Q1 (must use `idx_allocations_channel_performance`)
- Execution time > 2x SLO threshold (e.g., Q1 > 1000ms in typical case)
- No index usage for P0 queries (all scans are sequential)
- Planning time > 100ms (indicates query complexity issues)

**Red-Flag Response**: If any red-flag condition is present in AFTER plans, remediation is incomplete. Must:
1. Investigate why index is not being used
2. Adjust index definition or query if needed
3. Re-run EXPLAIN ANALYZE until red flags are resolved

### 5.4 Performance Exit Gate Definition

> **B0.3 OLAP Readiness Gate**: B0.3 is not complete until:
>
> 1. All P0 queries (Q1-Q5) meet their p95 SLOs on benchmark dataset
> 2. All 10 EXPLAIN ANALYZE outputs are captured and stored in `docs/performance/b0.3-query-plans.md`
> 3. "AFTER" plans show intended indexes are used (Index Scan or Index Only Scan)
> 4. No red-flag conditions are present in AFTER plans
> 5. Formal sign-off from B0.4 and B2.6 leads confirming queries meet their needs

**Gate Status**: 
- [ ] All P0 queries meet SLOs
- [ ] All EXPLAIN ANALYZE outputs captured
- [ ] Index usage confirmed
- [ ] No red flags present
- [ ] Sign-offs obtained

**Exit Gate 5**: Implementation Document contains complete `5.1-5.4` sections with explicit numeric thresholds and written statement linking B0.3 readiness to SLO compliance.

**SLO Validation Status**:
- [ ] Q1 SLO met: Execution Time < 500ms (typical)
- [ ] Q2 SLO met: Execution Time < 100ms (typical)
- [ ] Q3 SLO met: Execution Time < 250ms (typical)
- [ ] Q4 SLO met: Execution Time < 10ms (typical)
- [ ] Q5 SLO met: Execution Time < 300ms (typical)

---

## Phase 6: System-Level OLAP & Indexing Alignment

### 6.1 OLAP Readiness Checklist

**Pre-Completion Checklist**:

- [ ] All P0 and P1 queries explicitly defined and documented (Section 1.2)
- [ ] Canonical index list defined; each index maps to at least one query (Section 3.2)
- [ ] JSONB/GIN decisions explicit and justified (Section 3.3)
- [ ] Benchmark dataset profile documented (Section 2.4)
- [ ] EXPLAIN ANALYZE outputs captured for all P0 queries (Section 4.3)
- [ ] All P0 queries meet SLOs; no red-flag conditions (Section 5.4)
- [ ] Formal sign-offs from B0.4 and B2.6 leads (Section 1.2)

**Checklist Status**: Track completion of each item above.

### 6.2 New Query Governance (V1 Framework)

**Process for onboarding new OLAP queries**:

When a new dashboard or worker query is introduced:

1. **Classify Priority**: Determine if query is P0, P1, or P2
2. **Add to RQW**: If P0/P1, add query to `Representative Queries` section (Section 1.2)
3. **Map to Indexes**: 
   - Check if existing indexes support the query
   - If not, design new index following Query → Index Mapping process (Section 3.1)
4. **Benchmark**: Run EXPLAIN ANALYZE on benchmark dataset
5. **Evaluate SLOs**: Compare performance against appropriate SLO threshold
6. **Document**: Update Implementation Document with new query and index rationale
7. **Validate**: Ensure no red-flag conditions introduced

**Governance Principle**: No new P0 OLAP query goes into production without going through this process.

**Rationale**: Prevents index drift and ensures all OLAP queries have documented performance characteristics.

### 6.3 Architecture Alignment Notes

**Documentation Requirements**:

- SLOs and index policies defined in this document must be reflected in the **B0.3 section of the Backend Architecture Guide**
- This Implementation Document serves as the source of truth for OLAP performance requirements
- Future architecture updates must reference this document for OLAP/indexing decisions

**Alignment Status**:
- [ ] Backend Architecture Guide updated with B0.3 OLAP SLOs
- [ ] Index policy documented in architecture guide
- [ ] Cross-reference added from architecture guide to this document

### 6.4 Implementation DDL (V2 Remediation Migration)

**Migration File**: `alembic/versions/003_data_governance/remediate_b03_olap_indexes.py`

**Migration Template**:

```python
"""remediate_b03_olap_indexes

Remediate B0.3 OLAP indexing gaps:
- Create canonical idx_allocations_channel_performance index
- Create idx_revenue_ledger_tenant_state partial index
- Drop non-canonical indexes that drifted from specification

Revision ID: remediate_b03_olap_indexes
Revises: <previous_revision>
Create Date: 2025-11-17 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remediate_b03_olap_indexes'
down_revision = '<previous_revision>'  # Update with actual revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Remediate OLAP indexing gaps.
    
    Steps:
    1. Drop non-canonical indexes
    2. Create canonical composite index for Q1
    3. Create partial index for Q5
    """
    
    # Step 1: Drop non-canonical indexes
    op.execute("""
        DROP INDEX IF EXISTS idx_attribution_allocations_tenant_created_at;
    """)
    
    op.execute("""
        DROP INDEX IF EXISTS idx_attribution_allocations_channel;
    """)
    
    # Step 2: Create canonical composite index for Q1 (Channel Performance)
    op.execute("""
        CREATE INDEX idx_allocations_channel_performance 
        ON attribution_allocations (tenant_id, channel_code, created_at DESC) 
        INCLUDE (allocated_revenue_cents, allocation_ratio);
    """)
    
    # Step 3: Create partial index for Q5 (Real-time Revenue)
    # Note: Adjust column names if schema differs (state vs is_verified)
    op.execute("""
        CREATE INDEX idx_revenue_ledger_tenant_state 
        ON revenue_ledger (tenant_id, state) 
        WHERE state = 'captured';
    """)
    
    # Alternative if current schema uses is_verified:
    # op.execute("""
    #     CREATE INDEX idx_revenue_ledger_tenant_verified 
    #     ON revenue_ledger (tenant_id, is_verified) 
    #     WHERE is_verified = TRUE;
    # """)


def downgrade() -> None:
    """
    Reverse remediation changes.
    
    Steps:
    1. Drop new indexes
    2. Recreate old indexes
    """
    
    # Step 1: Drop new indexes
    op.execute("""
        DROP INDEX IF EXISTS idx_revenue_ledger_tenant_state;
    """)
    
    op.execute("""
        DROP INDEX IF EXISTS idx_allocations_channel_performance;
    """)
    
    # Step 2: Recreate old indexes
    op.execute("""
        CREATE INDEX idx_attribution_allocations_tenant_created_at 
        ON attribution_allocations (tenant_id, created_at DESC);
    """)
    
    op.execute("""
        CREATE INDEX idx_attribution_allocations_channel 
        ON attribution_allocations (channel_code);
    """)
```

**Migration Notes**:
- **DO NOT COMMIT** this migration until EXPLAIN ANALYZE validation is complete
- Adjust DDL based on actual schema state (column names may differ)
- Verify existing indexes before dropping (check if they exist and match expected names)
- Test downgrade() function to ensure reversibility

**Migration Status**:
- [ ] Migration file created (documented, not committed)
- [ ] DDL validated against actual schema
- [ ] Downgrade function tested

**Exit Gate 6**: Implementation Document contains complete `6.1-6.4` sections with readiness checklist, governance process, and full DDL for remediation migration.

---

## Verification Protocol

**No phase advancement without**:

1. **Artifact completion** matching both V1 documentation standards AND V2 specific outputs
2. **Empirical validation** showing index usage and performance compliance
3. **Formal sign-off** from relevant system owners (B0.4/B2.6 per V2)

**Final Deliverable Checklist**:

- [ ] Single Implementation Document (`REMEDIATION-B0.3-OLAP-DESIGN.md`) complete ✅
- [ ] All 6 phases documented with required sections ✅
- [ ] 10 EXPLAIN ANALYZE outputs captured in `docs/performance/b0.3-query-plans.md` (pending execution)
- [ ] Remediation migration DDL documented (Section 6.4, not committed)
- [ ] All P0 queries meet < 500ms p95 SLO (pending validation)
- [ ] Formal sign-offs obtained (pending)

**Verification Status**: Track completion of each deliverable above.

---

## Alignment with Channel Governance

This remediation aligns with completed B0.1-B0.2 phases and channel governance remediation:

- **Indexes respect FK constraints**: `idx_allocations_channel_performance` uses `channel_code` which has FK to `channel_taxonomy.code`
- **Queries use normalized channels**: Q1 uses `channel_code` (normalized via channel governance)
- **Performance validation**: Ensures channel performance queries (Q1) are optimized for dashboard use

**Channel Governance Integration**:
- Channel taxonomy state machine (from channel governance remediation) does not affect OLAP queries
- Channel assignment corrections (from channel governance) are post-ingestion and don't impact Q1-Q5 performance
- OLAP queries benefit from channel normalization (consistent `channel_code` values via FK constraint)

---

## File Structure

**Primary Deliverable**:
- `docs/database/REMEDIATION-B0.3-OLAP-DESIGN.md` (this file) ✅

**Supporting Artifacts** (created during execution, not in initial plan):
- `docs/performance/b0.3-query-plans.md` (10 EXPLAIN ANALYZE outputs) - **Pending**
- `alembic/versions/003_data_governance/remediate_b03_olap_indexes.py` (migration - documented in Section 6.4, not committed) - **Pending**

---

## Appendix A: Schema Alignment Notes

**Current Schema vs Canonical Schema Differences**:

This remediation assumes migration to canonical schema structure. Key differences to verify:

1. **`attribution_events`**:
   - Canonical: `event_timestamp`, `processing_status`, `idempotency_key`
   - Current: May use `occurred_at`, missing `processing_status` or `idempotency_key`
   - **Action**: Verify columns exist before running queries

2. **`attribution_allocations`**:
   - Canonical: `channel`, `confidence_score`
   - Current: `channel_code`, `allocation_ratio`
   - **Action**: Queries use `channel_code` (current schema). Index uses `channel_code`.

3. **`revenue_ledger`**:
   - Canonical: `state`, `amount_cents`
   - Current: `is_verified`, `revenue_cents`
   - **Action**: Q5 query and index must match actual schema. If `is_verified` exists, use that instead of `state`.

**Schema Verification Checklist**:
- [ ] Verify `attribution_events` columns match query assumptions
- [ ] Verify `attribution_allocations` columns match query assumptions
- [ ] Verify `revenue_ledger` columns match query assumptions
- [ ] Adjust queries and DDL if schema differs

---

## Appendix B: Query Parameter Examples

**Example UUIDs for Benchmark Dataset** (use deterministic generation):

```sql
-- Moderate tenant (typical case)
'moderate-tenant-uuid-0001'

-- Largest tenant (worst case)
'largest-tenant-uuid-0001'
```

**Example Date Ranges**:

```sql
-- Typical case (30 days)
'2024-01-01' AND '2024-01-31'

-- Worst case (90 days)
'2024-01-01' AND '2024-03-31'
```

**Example Idempotency Keys**:

```sql
-- Existing key (hit case)
'existing-idempotency-key-12345'

-- Non-existent key (miss case)
'non-existent-key-99999'
```

---

## Document Status

**Version**: 1.0  
**Last Updated**: 2025-11-17  
**Status**: Implementation Document Complete - Ready for Phase Execution  
**Next Steps**: 
1. Obtain sign-offs from B0.4 and B2.6 leads (Section 1.2)
2. Generate benchmark dataset (Section 2.4)
3. Capture EXPLAIN ANALYZE outputs (Section 4.2)
4. Validate SLO compliance (Section 5.4)
5. Create and test remediation migration (Section 6.4)

---

**END OF IMPLEMENTATION DOCUMENT**




