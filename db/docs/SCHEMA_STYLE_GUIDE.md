# Schema Style Guide

This document defines naming conventions, patterns, and standards for all database schema objects in Skeldir.

## Naming Conventions

### Tables and Columns

**snake_case** for all table and column names.

**Examples**:
- ✅ `attribution_events`
- ✅ `tenant_id`
- ✅ `created_at`
- ❌ `AttributionEvents` (PascalCase)
- ❌ `tenantId` (camelCase)
- ❌ `created-at` (kebab-case)

**Rationale**: PostgreSQL convention, consistent with Python naming, easier to read in SQL.

### Primary Keys

**Pattern**: `id uuid PRIMARY KEY DEFAULT gen_random_uuid()`

**Example**:
```sql
CREATE TABLE attribution_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
);
```

**Rationale**: 
- UUID provides globally unique identifiers
- `gen_random_uuid()` is PostgreSQL native (no extension required)
- UUIDs prevent enumeration attacks and enable distributed systems

**Anti-patterns**:
- ❌ `id serial` (sequential IDs reveal information)
- ❌ `id bigserial` (same issue)
- ❌ Custom UUID generation (use PostgreSQL native)

### Timestamps

**Pattern**: Timestamp trio for most tables:
- `created_at timestamptz NOT NULL DEFAULT now()`
- `updated_at timestamptz NOT NULL DEFAULT now()`
- Domain-specific temporal columns as needed (e.g., `event_timestamp`, `processed_at`)

**Example**:
```sql
CREATE TABLE attribution_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    event_timestamp timestamptz NOT NULL,  -- Domain-specific
    ...
);
```

**Rationale**:
- `timestamptz` (timestamp with time zone) ensures correct timezone handling
- `NOT NULL` prevents null timestamps
- `DEFAULT now()` provides automatic timestamping
- Domain-specific columns for business logic timestamps

**Anti-patterns**:
- ❌ `timestamp` (without timezone) - loses timezone information
- ❌ `created_at timestamp` - missing timezone
- ❌ `created_at timestamptz NULL` - allows null timestamps

### Boolean Columns

**Pattern**: Use prefixes `is_*`, `has_*`, or `can_*` for boolean columns.

**Examples**:
- ✅ `is_verified`
- ✅ `has_errors`
- ✅ `can_process`
- ❌ `verified` (unclear if boolean)
- ❌ `errors` (unclear if boolean)

**Rationale**: Prefixes make boolean intent explicit and improve readability.

### Foreign Keys

**Pattern**: `{referenced_table}_id` (singular form of referenced table name)

**Examples**:
- ✅ `tenant_id` (references `tenants` table)
- ✅ `event_id` (references `attribution_events` table)
- ✅ `user_id` (references `users` table)
- ❌ `tenant` (missing `_id` suffix)
- ❌ `tenants_id` (plural form)

**Rationale**: Consistent naming makes relationships clear and follows PostgreSQL conventions.

### Check Constraints

**Pattern**: `ck_{table}_{column}_{condition}`

**Examples**:
- ✅ `ck_attribution_events_revenue_cents_positive` (CHECK revenue_cents >= 0)
- ✅ `ck_revenue_ledger_status_valid` (CHECK status IN ('pending', 'processed', 'failed'))
- ❌ `check_revenue` (too generic)
- ❌ `revenue_check` (wrong order)

**Rationale**: Descriptive names help identify constraint purpose and location.

### Indexes

**Pattern**: `idx_{table}_{columns}`

**Examples**:
- ✅ `idx_attribution_events_tenant_timestamp` (on `tenant_id, event_timestamp DESC`)
- ✅ `idx_revenue_ledger_tenant_created` (on `tenant_id, created_at DESC`)
- ✅ `idx_attribution_events_session_id` (on `session_id`)
- ❌ `index1` (not descriptive)
- ❌ `attribution_events_idx` (wrong order)

**For partial indexes**, include condition in name:
- ✅ `idx_attribution_events_tenant_active` (WHERE status = 'active')

**Rationale**: Consistent naming makes indexes discoverable and their purpose clear.

## Comment Requirements

**All database objects must have comments** using `COMMENT ON` statements.

**Minimum Content**:
- **Purpose**: What the object is used for
- **Data Class**: PII/non-PII classification
- **Ownership**: Which team/component owns this object

**Example**:
```sql
COMMENT ON TABLE attribution_events IS 'Stores attribution events for revenue tracking. Non-PII data only. Owned by attribution service.';
COMMENT ON COLUMN attribution_events.revenue_cents IS 'Revenue amount in cents (INTEGER). Purpose: Store revenue for attribution calculations. Data class: Non-PII.';
```

**Rationale**: Comments enable data dictionary generation and improve schema legibility.

## Revenue Storage

**Pattern**: `INTEGER` (cents), **never** `DECIMAL` or `FLOAT`

**Example**:
```sql
revenue_cents INTEGER NOT NULL CHECK (revenue_cents >= 0)
```

**Rationale** (per `.cursor/rules:164`):
- Integer arithmetic is exact (no floating-point errors)
- Better performance than DECIMAL
- Cents provide sufficient precision for currency
- API converts to float (dollars) in responses: `revenue_cents / 100.0`

**Anti-patterns**:
- ❌ `revenue DECIMAL(10, 2)` (floating-point issues, performance)
- ❌ `revenue FLOAT` (precision loss, performance)
- ❌ `revenue NUMERIC` (overhead, unnecessary precision)

## JSONB Usage

**Pattern**: Use `JSONB` columns for raw payloads and semi-structured data.

**Example**:
```sql
raw_payload JSONB NOT NULL
```

**With GIN Index** (per `.cursor/rules:165`):
```sql
CREATE INDEX idx_attribution_events_raw_payload ON attribution_events USING GIN (raw_payload);
```

**Rationale**:
- JSONB provides efficient storage and querying of semi-structured data
- GIN indexes enable fast JSON queries
- Useful for webhook payloads, metadata, and flexible schemas

**When to Use**:
- Raw webhook payloads (before PII stripping)
- Metadata that doesn't fit relational structure
- Configuration data

**When NOT to Use**:
- Core business data (use relational columns)
- Frequently queried fields (extract to columns)
- Data requiring referential integrity (use FKs)

## Comment Standard

**Requirement**: All database objects must have comments using `COMMENT ON` statements.

**Minimum Content**:
- **Purpose**: What the object is used for
- **Data Class**: PII/non-PII classification
- **Ownership**: Which team/component owns this object

**Example - Table Comment**:
```sql
COMMENT ON TABLE attribution_events IS 
    'Stores attribution events for revenue tracking. Purpose: Event ingestion and attribution calculations. Data class: Non-PII. Ownership: Attribution service.';
```

**Example - Column Comment**:
```sql
COMMENT ON COLUMN attribution_events.revenue_cents IS 
    'Revenue amount in cents (INTEGER). Purpose: Store revenue for attribution calculations. Data class: Non-PII.';
```

**Example - Policy Comment**:
```sql
COMMENT ON POLICY tenant_isolation_policy ON attribution_events IS 
    'RLS policy enforcing tenant isolation. Purpose: Prevent cross-tenant data access.';
```

**Rationale**: Comments enable data dictionary generation and improve schema legibility.

**See Also**: `TRACEABILITY_STANDARD.md` for correlation_id and actor_* metadata conventions.

## Cross-References

- **Contract Mapping**: See `CONTRACT_TO_SCHEMA_MAPPING.md` for OpenAPI → PostgreSQL type mappings
- **RLS Templates**: See `db/migrations/templates/rls_policy.py.template` for tenant isolation patterns
- **Lint Rules**: See `DDL_LINT_RULES.md` for enforcement rules
- **Traceability**: See `TRACEABILITY_STANDARD.md` for correlation_id and actor_* metadata

