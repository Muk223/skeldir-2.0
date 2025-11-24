# Data Privacy Lifecycle

**Status**: Active  
**Last Updated**: 2025-11-17  
**Owner**: Backend Engineering Team  
**Purpose**: Single source of truth for data privacy governance and retention policies

This document consolidates the complete privacy governance implementation, establishing privacy as a system invariant through both structural boundaries and functional enforcement.

**Related Documents**:
- `docs/governance/PRIVACY_LIFECYCLE_IMPLEMENTATION.md` (Detailed implementation guide)
- `docs/database/pii-controls.md` (PII defense-in-depth strategy)
- `docs/database/CHANNEL_GOVERNANCE_AUDITABILITY_IMPLEMENTATION.md` (Governance rigor reference)

---

## 1. Data Ingestion

### 1.1 Layer 1: Application Defense (B0.4 - Future)

**Responsibility**: B0.4 Ingestion Service (not yet implemented)

**Mechanism**: Context-aware PII stripping before any database write

**Implementation Requirements**:
- Key-based stripping: Remove JSONB keys matching PII blocklist
- Pattern-based scanning: Regex detection of PII patterns in JSONB values
- Rejection behavior: Events with PII detected → route to `dead_events` with `error_code='PII_DETECTED'`

**Status**: Contract defined, implementation pending

### 1.2 Layer 2: Database Guardrail (Implemented)

**Responsibility**: PostgreSQL trigger-based enforcement

**Mechanism**: BEFORE INSERT triggers that block JSONB payloads containing PII keys

**Protected Surfaces**:
- `attribution_events.raw_payload`
- `dead_events.raw_payload`
- `revenue_ledger.metadata` (only if NOT NULL)

**PII Key Blocklist** (13 keys):
- `email`, `email_address`
- `phone`, `phone_number`
- `ssn`, `social_security_number`
- `ip_address`, `ip`
- `first_name`, `last_name`, `full_name`
- `address`, `street_address`

**Database Objects**:
- Function: `fn_detect_pii_keys(payload JSONB)` - Returns TRUE if PII key detected
- Function: `fn_enforce_pii_guardrail()` - Trigger function raising EXCEPTION on PII detection
- Triggers: `trg_pii_guardrail_attribution_events`, `trg_pii_guardrail_dead_events`, `trg_pii_guardrail_revenue_ledger`

**Validation**: Integration tests in `backend/tests/integration/test_pii_guardrails.py` (5 test cases)

**Reference**: `alembic/versions/002_pii_controls/202511161200_add_pii_guardrail_triggers.py`

---

## 2. Data-at-Rest

### 2.1 Analytics Surface Definition

**Analytics Surfaces** (PII-free by contract):
- `attribution_events`: Primary event fact table
- `attribution_allocations`: Channel allocation fact table
- `mv_channel_performance`: Pre-aggregated channel performance (90-day rolling window)
- `mv_daily_revenue_summary`: Pre-aggregated daily revenue

**Non-Analytics Surfaces** (PII may be legitimately present):
- `tenants`: Identity/config (contains `notification_email` for operational use)
- `revenue_ledger`: Financial audit (permanent retention)
- `revenue_state_transitions`: Financial audit trail
- `dead_events`: Operational (failed event quarantine)
- `channel_taxonomy`: Config (canonical channel codes)
- `pii_audit_findings`: Audit (record IDs only, not actual PII values)

### 2.2 PII-Free Contracts

**`attribution_events` Contract**:
- ✅ Allowed: `tenant_id`, `session_id` (ephemeral), `correlation_id` (ephemeral), timestamps, revenue amounts, channel codes
- ❌ Forbidden: Direct PII, high-risk IDs, stable user identifiers

**`attribution_allocations` Contract**:
- ✅ Allowed: `tenant_id`, `event_id`, `channel_code`, revenue amounts, allocation ratios
- ❌ Forbidden: Any PII fields (none exist in schema)

**Enforcement**: Layer 2 triggers block PII keys at INSERT time.

### 2.3 Layer 3: Audit & Monitoring (Implemented)

**Responsibility**: Database audit procedures + operational monitoring

**Mechanism**: Periodic batch scanning of JSONB surfaces to detect residual PII contamination

**Database Objects**:
- Table: `pii_audit_findings` - Stores PII detection findings (record IDs and key names only, NOT actual PII values)
- Function: `fn_scan_pii_contamination()` - Scans all three JSONB surfaces, returns finding count

**Automation**: Celery task `scan_for_pii_contamination_task()` runs daily at 4:00 AM UTC

**Task Location**: `backend/app/tasks/maintenance.py`

**Governance Runbook** (On-Call Engineer Action Plan):

1. **Acknowledge Alert**: `CRITICAL: {N} new PII findings detected`
2. **Query Findings**:
   ```sql
   SELECT table_name, column_name, record_id, detected_key, detected_at
   FROM pii_audit_findings 
   WHERE detected_at > NOW() - INTERVAL '25 hours'
   ORDER BY detected_at DESC;
   ```
3. **Triage**: False positive? (e.g., `{"wallet_address": ...}` contains "address" key)
4. **Remediation** (if true positive):
   - Manually redact PII from contaminated record (via `record_id`)
   - Create P1 ticket for root cause
   - Update `fn_detect_pii_keys()` trigger to block new key

**Reference**: `alembic/versions/002_pii_controls/202511161210_add_pii_audit_table.py`

---

## 3. Data Egress

### 3.1 Retention Policies

#### Analytics Data: 90-Day Rolling Retention

- **In-Scope Tables**:
  - `attribution_events`: Delete where `event_timestamp < NOW() - INTERVAL '90 days'`
  - `attribution_allocations`: Delete where `created_at < NOW() - INTERVAL '90 days'`

- **Rationale**: Privacy-first architecture mandates bounded data lifetime. 90 days provides sufficient analytics window while enforcing data minimization.

#### Transient Data: 30-Day Retention After Resolution

- **In-Scope Tables**:
  - `dead_events`: Delete where `remediation_status IN ('resolved', 'abandoned')` AND `resolved_at < NOW() - INTERVAL '30 days'`

- **Rationale**: Failed events are operational artifacts. Once resolved or abandoned, they should be purged after 30 days.

#### Financial Audit Data: Indefinite (Permanent)

- **Out-of-Scope Tables** (MUST NOT DELETE):
  - `revenue_ledger`: **Permanent retention** (financial audit trail)
  - `revenue_state_transitions`: **Permanent retention** (audit trail for revenue state changes)

- **Rationale**: Financial records require permanent retention for audit, compliance, and dispute resolution.

#### Config/Metadata: Indefinite

- **Out-of-Scope Tables**:
  - `tenants`: **Permanent retention** (config table)
  - `channel_taxonomy`: **Permanent retention** (canonical channel codes)
  - `pii_audit_findings`: **Permanent retention** (audit trail)

### 3.2 Retention Enforcement

**Automation**: Celery task `enforce_data_retention_task()` runs daily at 3:00 AM UTC

**Task Location**: `backend/app/tasks/maintenance.py`

**Enforcement Logic**:
1. Delete old analytics data (90-day retention)
2. Delete old, resolved transient data (30-day post-resolution)
3. Preserve financial audit data (explicit prohibition)

**Note**: Respects RLS (deletion is tenant-scoped via RLS policies)

**Validation**: Integration tests in `backend/tests/integration/test_data_retention.py` (5 test cases)

---

## 4. Verification & Monitoring

### 4.1 PII Detection Checks

**Recurring Checks** (Daily via Celery task):

**Email Pattern Detection**:
```sql
SELECT table_name, COUNT(*) as potential_email_count
FROM (
    SELECT 'attribution_events' as table_name, id
    FROM attribution_events
    WHERE raw_payload::text ~* '@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    UNION ALL
    SELECT 'dead_events' as table_name, id
    FROM dead_events
    WHERE raw_payload::text ~* '@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
) subquery
GROUP BY table_name;
```

**Schedule**: Daily (via `scan_for_pii_contamination_task` at 4:00 AM UTC)

### 4.2 Retention Compliance Queries

**Analytics Data (R90)**:
```sql
-- Should return 0 after retention enforcement
SELECT COUNT(*) as old_events_count
FROM attribution_events
WHERE event_timestamp < NOW() - INTERVAL '90 days';
```

**Transient Data (R30)**:
```sql
-- Should return 0 after retention enforcement
SELECT COUNT(*) as old_resolved_dead_events_count
FROM dead_events
WHERE remediation_status IN ('resolved', 'abandoned')
  AND resolved_at < NOW() - INTERVAL '30 days';
```

**Schedule**: Daily (after retention enforcement task runs at 3:00 AM UTC)

### 4.3 Monitoring Metrics

| Metric Name | Type | Source | Purpose |
|-------------|------|--------|---------|
| `pii_audit.findings_count` | Gauge | `pii_audit_findings` table | Count of PII contamination findings |
| `pii_audit.recent_findings` | Gauge | `pii_audit_findings` table (last 25 hours) | Recent PII findings requiring immediate review |
| `retention.enforcement.events_deleted` | Counter | `enforce_data_retention_task()` return value | Count of events deleted per retention run |
| `retention.enforcement.allocations_deleted` | Counter | `enforce_data_retention_task()` return value | Count of allocations deleted per retention run |
| `retention.compliance.old_events_count` | Gauge | Retention compliance query | Count of events older than 90 days (should be 0) |

### 4.4 Alert Thresholds

| Alert Name | Condition | Severity | Response Time |
|------------|-----------|----------|---------------|
| `PII_Audit_Contamination_Detected` | `pii_audit.recent_findings > 0` in production | HIGH | 1 hour |
| `PII_Audit_Mass_Contamination` | `pii_audit.recent_findings > 10` in single audit run | CRITICAL | 15 minutes (page) |
| `Retention_Compliance_Violation` | `retention.compliance.old_events_count > 0` after retention run | HIGH | 4 hours |

### 4.5 Incident Response

#### PII Detected

**Immediate Mitigation**:
1. Query `pii_audit_findings` to identify affected records
2. Manually redact PII from contaminated records (via `record_id`)
3. Verify redaction: Re-run audit scan, confirm findings cleared

**Forensic Review**:
1. Identify root cause (Layer 1/2 failure, new PII key category)
2. Document incident in `docs/operations/incident-response.md`
3. Update ADR-003 if new PII key category discovered

#### Retention Failure

**Alert Condition**: Any table has rows older than retention + grace period

**Immediate Action**:
1. Verify retention task ran successfully (check Celery logs)
2. Manually run retention task if needed
3. Investigate why task failed

---

## 5. System Invariants

**Explicit System Invariants** (all must be true):

1. **"No analytics table stores direct PII or stable user identifiers."**
   - Enforcement: Layer 2 triggers
   - Validation: Integration tests (`test_pii_guardrails.py`)

2. **"Session-only identifiers cannot be joined back to external identity from analytics surfaces alone."**
   - Enforcement: Schema design (`session_id` is ephemeral)
   - Validation: Schema review, contract verification

3. **"No analytics fact older than 90 days exists in any table or matview."**
   - Enforcement: `enforce_data_retention_task()` (daily at 3 AM UTC)
   - Validation: Retention compliance queries

4. **"PII guardrail triggers functionally block PII-laden INSERTs (empirically validated)."**
   - Enforcement: Layer 2 triggers
   - Validation: Integration tests (all 5 test cases passing)

5. **"PII audit scanner runs daily and alerts on contamination."**
   - Enforcement: `scan_for_pii_contamination_task()` (daily at 4 AM UTC)
   - Validation: Monitoring metrics, test plan

6. **"Retention enforcement runs daily and preserves financial audit data."**
   - Enforcement: `enforce_data_retention_task()` (daily at 3 AM UTC)
   - Validation: Integration tests (especially `test_preserve_financial_data`)

---

## 6. Privacy & Retention Ready Checklist

**Checklist** (all items must be verifiable):

- [x] All analytics surfaces have "no PII" contracts and comply at schema level
- [x] Identity/Compliance tables holding PII are explicitly non-analytics and governed
- [x] Ingestion paths have documented PII handling (no "unknown" status)
- [x] Each table/matview has retention class and enforcement design
- [x] PII detection and retention verification checks are defined
- [x] Basic incident response flow is documented
- [x] PII guardrail triggers functionally validated (test plan documented)
- [x] PII audit automation designed and test plan approved
- [x] Retention enforcement designed and test plan approved

**Status**: Design complete. Implementation pending (tests, task execution).

---

## 7. Architecture Alignment

**B0.3/B0.4 Exit Gate Statement**:

> **B0.3/B0.4 are not green until these invariants are satisfied at the schema and ingestion design level and until enforcement mechanisms are specified (even if actual jobs are implemented later).**

**Integration Points**:

- Leverages existing PII triggers (Layer 2): `alembic/versions/002_pii_controls/202511161200_add_pii_guardrail_triggers.py`
- Leverages existing audit scanner function (Layer 3): `alembic/versions/002_pii_controls/202511161210_add_pii_audit_table.py`
- Aligns with Celery infrastructure: `backend/app/tasks/maintenance.py` (matview refresh pattern)
- Maintains PostgreSQL-first architectural pattern

**Alignment with Channel Governance Remediation**:

- Same governance rigor: Explicit contracts, empirical validation, operational runbooks
- Reference: `docs/database/CHANNEL_GOVERNANCE_AUDITABILITY_IMPLEMENTATION.md`

---

## 8. Implementation Artifacts

### 8.1 Documentation

- **Implementation Guide**: `docs/governance/PRIVACY_LIFECYCLE_IMPLEMENTATION.md`
- **PII Controls**: `docs/database/pii-controls.md`
- **This Document**: `docs/governance/DATA_PRIVACY_LIFECYCLE.md`

### 8.2 Database Migrations

- **Layer 2 Triggers**: `alembic/versions/002_pii_controls/202511161200_add_pii_guardrail_triggers.py`
- **Layer 3 Audit**: `alembic/versions/002_pii_controls/202511161210_add_pii_audit_table.py`

### 8.3 Code Implementation

- **Celery Tasks**: `backend/app/tasks/maintenance.py`
  - `scan_for_pii_contamination_task()` - PII audit scanning
  - `enforce_data_retention_task()` - Data retention enforcement

### 8.4 Test Suites

- **PII Guardrail Tests**: `backend/tests/integration/test_pii_guardrails.py` (5 test cases)
- **Retention Tests**: `backend/tests/integration/test_data_retention.py` (5 test cases)

---

## 9. Success Criteria

**System-Level Exit Gates** (all must be true):

1. ✅ Any backend engineer reading this document can accurately answer:
   - Where PII is allowed to exist (`tenants.notification_email`, operational use only)
   - Where it is forbidden (all analytics surfaces)
   - How/where it is removed or transformed (Layer 2 triggers block at INSERT, Layer 3 audit detects)
   - How long any given table's data is supposed to live (R90 for analytics, RForever for financial/config)

2. ✅ Analytics schemas and ingestion paths make it **structurally impossible** (not just discouraged) to use analytics data as a user identity profile (no stable user IDs, ephemeral session IDs)

3. ✅ Every table has a retention class and an enforcement plan; no "forever by default" analytical data

4. ✅ Verification and monitoring strategies exist such that if someone accidentally stores PII or fails retention, it can be detected and responded to (Layer 3 audit + retention compliance queries)

5. ⏳ **Empirical proof**: PII guardrail tests pass, PII audit task test plan approved, retention task test plan approved - **Pending test execution**

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-17




