# B0.3 → B0.4 Handoff Contract

**Version:** 1.0.0  
**Date:** 2025-11-17  
**Status:** Contract Document  
**Related Document:** `docs/database/REMEDIATION-B0.3-GOVERNANCE-SYSTEM-DESIGN.md`

---

## Purpose

This contract defines the formal handoff between B0.3 (Database Schema Foundation) and B0.4 (Ingestion Service). It makes B0.3's guarantees explicit and B0.4's responsibilities non-negotiable.

---

## B0.3 Guarantees (The "Provide")

B0.3 provides the following **guaranteed** capabilities to B0.4:

### 1. Idempotency Guarantee

**Guarantee**: B0.3 provides a `UNIQUE` constraint on `(tenant_id, idempotency_key)` in `attribution_events`. The database **will** reject duplicate ingestion events.

**Implementation**:
- Table: `attribution_events`
- Constraint: `UNIQUE INDEX idx_events_idempotency ON attribution_events (idempotency_key)`
- Error: `UniqueViolation` exception raised on duplicate `idempotency_key`

**Evidence**:
```sql
CREATE UNIQUE INDEX idx_events_idempotency ON attribution_events (idempotency_key);
```

**Validation**: 
- Insert with duplicate `idempotency_key` → `UniqueViolation` error
- Query: `SELECT COUNT(*) FROM attribution_events WHERE idempotency_key = '<key>';` → returns 0 or 1

---

### 2. RLS Guarantee

**Guarantee**: B0.3 guarantees RLS is **functionally wired**. Any API-authenticated DB session **will** have its `app.current_tenant_id` set, enforcing tenant isolation.

**Implementation**:
- RLS policies on all tenant-scoped tables: `attribution_events`, `attribution_allocations`, `revenue_ledger`, `dead_events`, `reconciliation_runs`
- Policy: `tenant_isolation_policy` using `current_setting('app.current_tenant_id')::UUID`
- Application middleware sets GUC: `SET LOCAL app.current_tenant_id = '<tenant_id>';`

**Evidence**:
```sql
CREATE POLICY tenant_isolation_policy ON attribution_events
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

**Validation**:
- Query without `app.current_tenant_id` set → returns 0 rows
- Query with `app.current_tenant_id` set → returns only tenant's data
- Cross-tenant queries blocked by RLS

---

### 3. Performance Guarantee

**Guarantee**: B0.3 provides the **validated** indexes from the Representative Query Workload (RQW). Ingestion queries (Q2, Q4) **are guaranteed** to use `idx_events_processing_status` and `idx_events_idempotency`.

**Implementation**:
- Index: `idx_events_processing_status` on `(processing_status, processed_at) WHERE processing_status = 'pending'`
- Index: `idx_events_idempotency` on `idempotency_key` (UNIQUE)
- Index: `idx_allocations_channel_performance` on `(tenant_id, channel_code, created_at DESC) INCLUDE (allocated_revenue_cents, confidence_score)`

**Evidence**:
- EXPLAIN ANALYZE outputs stored in `docs/database/REMEDIATION-B0.3-OLAP-DESIGN.md`
- Indexes match canonical spec in `db/schema/canonical_schema.sql`

**Validation**:
- Query: `SELECT * FROM attribution_events WHERE processing_status = 'pending' ORDER BY processed_at LIMIT 100;`
- EXPLAIN shows index scan on `idx_events_processing_status`
- Query: `SELECT * FROM attribution_events WHERE idempotency_key = '<key>';`
- EXPLAIN shows index scan on `idx_events_idempotency`

---

### 4. Audit Guarantee

**Guarantee**: B0.3 guarantees that any `UPDATE` to `revenue_ledger.state` **will** be atomically recorded in `revenue_state_transitions` via database trigger.

**Implementation**:
- Trigger: `trg_revenue_state_audit` on `revenue_ledger`
- Trigger function: `fn_revenue_state_audit()` inserts into `revenue_state_transitions`
- Table: `revenue_state_transitions` (ledger_id, from_state, to_state, reason, transitioned_at)

**Evidence**:
```sql
CREATE TRIGGER trg_revenue_state_audit
    BEFORE UPDATE OF state ON revenue_ledger
    FOR EACH ROW
    EXECUTE FUNCTION fn_revenue_state_audit();
```

**Validation**:
- UPDATE `revenue_ledger.state` → automatic insert into `revenue_state_transitions`
- Query: `SELECT * FROM revenue_state_transitions WHERE ledger_id = '<id>';` → shows transition history

---

### 5. Privacy Guarantee

**Guarantee**: B0.3 guarantees that any `INSERT` with a PII key (e.g., 'email') in `raw_payload` **will be rejected** by the `trg_events_pii_guardrail` trigger.

**Implementation**:
- Trigger: `trg_events_pii_guardrail` on `attribution_events`
- Trigger function: `fn_detect_pii_keys()` scans JSONB for PII keys
- PII keys: `email`, `phone`, `ssn`, `ip_address`, `first_name`, `last_name`, `address`
- Behavior: Raises exception if PII keys detected

**Evidence**:
```sql
CREATE TRIGGER trg_events_pii_guardrail
    BEFORE INSERT OR UPDATE ON attribution_events
    FOR EACH ROW
    EXECUTE FUNCTION fn_detect_pii_keys();
```

**Validation**:
- INSERT with `raw_payload = '{"email": "user@example.com"}'` → exception raised
- INSERT with `raw_payload = '{"event_type": "click"}'` → succeeds

---

### 6. Retention Guarantee

**Guarantee**: B0.3 guarantees that a daily automated job **will** prune analytics data older than 90 days.

**Implementation**:
- Celery task or scheduled job (implementation pending)
- Retention policy: 90 days for analytics tables
- Tables affected: `attribution_events`, `attribution_allocations`, `revenue_ledger`, `dead_events`

**Evidence**:
- Retention task defined in `backend/app/tasks/` (implementation pending)
- Retention matrix documented in privacy Implementation Doc

**Validation**:
- Query: `SELECT COUNT(*) FROM attribution_events WHERE created_at < NOW() - INTERVAL '90 days';` → returns 0 after retention job runs

---

## B0.4 Responsibilities (The "Consume")

B0.4 must fulfill the following responsibilities to use B0.3 correctly:

### 1. Idempotency Responsibility

**Requirement**: The B0.4 service **must** generate and supply a non-null `idempotency_key` for every event. It **must** handle `UniqueViolation` errors.

**Implementation**:
- Generate `idempotency_key` for each ingestion event (e.g., hash of event payload + timestamp)
- Include `idempotency_key` in INSERT statement
- Catch `UniqueViolation` exception and treat as success (idempotent retry)

**Example**:
```python
try:
    db.execute(
        "INSERT INTO attribution_events (tenant_id, idempotency_key, ...) VALUES (...)",
        {"idempotency_key": generate_idempotency_key(event)}
    )
except UniqueViolation:
    # Event already ingested, treat as success
    log.info("Duplicate event detected, skipping")
```

**Validation**:
- B0.4 test suite verifies idempotent retry behavior
- Test: Insert same event twice → second insert succeeds (no error) but no duplicate row

---

### 2. RLS Responsibility

**Requirement**: The B0.4 service **must** use the standard authenticated database session. It **must not** attempt to bypass the RLS wiring.

**Implementation**:
- Use authenticated database connection (not superuser)
- Set `app.current_tenant_id` GUC before queries:
  ```python
  db.execute("SET LOCAL app.current_tenant_id = :tenant_id", {"tenant_id": tenant_id})
  ```
- Do not use superuser connections or `SET ROLE` to bypass RLS

**Prohibited Patterns**:
- ❌ Superuser connections
- ❌ `SET ROLE` to bypass RLS
- ❌ Direct table access without tenant context

**Validation**:
- B0.4 test suite verifies tenant isolation
- Test: Query without setting `app.current_tenant_id` → returns 0 rows
- Test: Query with wrong tenant_id → returns 0 rows

---

### 3. Performance Responsibility

**Requirement**: The B0.4 service **must not** introduce new, un-indexed query patterns (e.g., `raw_payload @> ...`) without **first** triggering a B0.3 remediation to add the required index.

**Implementation**:
- Use existing indexed columns for queries (`idempotency_key`, `processing_status`, `tenant_id`)
- Avoid JSONB queries (`raw_payload @> ...`) unless GIN index exists
- If new query pattern needed:
  1. Create ADR documenting query pattern
  2. Request B0.3 remediation to add GIN index
  3. Wait for index to be added before using query pattern

**Example**:
```python
# ✅ Good: Uses indexed column
events = db.execute(
    "SELECT * FROM attribution_events WHERE idempotency_key = :key",
    {"key": idempotency_key}
)

# ❌ Bad: Un-indexed JSONB query (unless GIN index exists)
events = db.execute(
    "SELECT * FROM attribution_events WHERE raw_payload @> '{\"channel\": \"google\"}'"
)
```

**Validation**:
- B0.4 code review checks for un-indexed query patterns
- EXPLAIN ANALYZE run on all B0.4 queries to verify index usage

---

### 4. Audit Responsibility

**Requirement**: The B0.4 service **must not** write to `revenue_state_transitions` directly. It **must only** `UPDATE revenue_ledger.state` and trust the trigger.

**Implementation**:
- Only write to `revenue_ledger` table
- Use `UPDATE revenue_ledger SET state = :new_state WHERE id = :ledger_id`
- Do not INSERT into `revenue_state_transitions` directly
- Trust trigger to create audit record

**Prohibited Patterns**:
- ❌ `INSERT INTO revenue_state_transitions (...)`
- ❌ Manual audit record creation

**Example**:
```python
# ✅ Good: Update state, trigger handles audit
db.execute(
    "UPDATE revenue_ledger SET state = :new_state WHERE id = :ledger_id",
    {"new_state": "verified", "ledger_id": ledger_id}
)

# ❌ Bad: Manual audit record
db.execute("INSERT INTO revenue_state_transitions (...) VALUES (...)")
```

**Validation**:
- B0.4 code review checks for direct `revenue_state_transitions` writes
- Test: UPDATE `revenue_ledger.state` → verify audit record created automatically

---

### 5. Privacy Responsibility

**Requirement**: The B0.4 service **should** perform application-level PII stripping, but it **must** rely on the B0.3 trigger as the final defense-in-depth.

**Implementation**:
- Strip PII from `raw_payload` before INSERT (application layer)
- Do not include PII keys (`email`, `phone`, `ssn`, etc.) in JSONB payload
- Trust B0.3 trigger to reject any PII that slips through

**Example**:
```python
# ✅ Good: Strip PII before INSERT
def strip_pii(payload):
    pii_keys = ['email', 'phone', 'ssn', 'ip_address', 'first_name', 'last_name', 'address']
    return {k: v for k, v in payload.items() if k not in pii_keys}

clean_payload = strip_pii(event.raw_payload)
db.execute(
    "INSERT INTO attribution_events (..., raw_payload) VALUES (..., :payload)",
    {"payload": json.dumps(clean_payload)}
)

# ❌ Bad: Include PII in payload (will be rejected by trigger)
db.execute(
    "INSERT INTO attribution_events (..., raw_payload) VALUES (..., :payload)",
    {"payload": json.dumps({"email": "user@example.com"})}  # Will fail
)
```

**Validation**:
- B0.4 test suite verifies PII stripping
- Test: Attempt INSERT with PII → exception raised by trigger

---

## Sign-Off Process

**B0.4 Lead Sign-Off**:

- [ ] B0.4 lead has reviewed all guarantees and responsibilities
- [ ] B0.4 lead confirms understanding of B0.3 capabilities
- [ ] B0.4 lead commits to fulfilling B0.4 responsibilities
- [ ] Sign-off recorded below with date and signature

**Sign-Off Record**:

```
B0.4 Lead: ____________________
Date: ________________________
Signature: ____________________

Notes: ______________________________________________
```

**B0.3 Lead Sign-Off**:

- [ ] B0.3 lead confirms all guarantees are implemented and validated
- [ ] B0.3 lead confirms B0.4 responsibilities are reasonable
- [ ] Sign-off recorded below with date and signature

```
B0.3 Lead: ____________________
Date: ________________________
Signature: ____________________

Notes: ______________________________________________
```

---

## Deviation Process

If B0.4 requires breaking any B0.3 guarantee or responsibility:

1. **Create ADR** documenting deviation request
2. **Get Architecture Review Approval**
3. **Update This Contract** to reflect new agreement
4. **Re-sign Contract** with updated terms

---

## Related Documents

- **Implementation Document**: `docs/database/REMEDIATION-B0.3-GOVERNANCE-SYSTEM-DESIGN.md`
- **Migration Policy**: `docs/database/RUNBOOK-MIGRATION-POLICY.md`
- **B0.3 OLAP Design**: `docs/database/REMEDIATION-B0.3-OLAP-DESIGN.md`
- **B0.3 Privacy Controls**: `docs/database/pii-controls.md`

---

**Contract Status**: ⚠️ Pending Sign-Off  
**Next Review**: After B0.4 implementation begins

