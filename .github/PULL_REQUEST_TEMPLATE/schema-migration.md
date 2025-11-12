# Schema Migration Pull Request

## Migration Details

- **Migration File**: `alembic/versions/YYYYMMDDHHMM_description.py`
- **Type**: [ ] Versioned DDL Change [ ] Repeatable Migration [ ] Extension Enablement
- **Description**: Brief description of schema changes

## Governance Compliance Checklist

### Style Guide Compliance
- [ ] Table/column names follow snake_case convention
- [ ] Primary key uses `id uuid PRIMARY KEY DEFAULT gen_random_uuid()`
- [ ] Timestamps use `timestamptz NOT NULL DEFAULT now()`
- [ ] Boolean columns use `is_*`/`has_*`/`can_*` prefixes
- [ ] Foreign keys use `{table}_id` naming
- [ ] Check constraints use `ck_{table}_{column}_{condition}` naming
- [ ] Indexes use `idx_{table}_{columns}` naming
- [ ] Revenue stored as `INTEGER` (cents), not `DECIMAL`/`FLOAT`
- [ ] JSONB columns have GIN indexes (if applicable)

### Contract Mapping Verification
- [ ] Type mappings follow `CONTRACT_TO_SCHEMA_MAPPING.md`
- [ ] Required contract fields are `NOT NULL` in database
- [ ] Enum handling follows rulebook (CHECK vs lookup table)
- [ ] Contract source referenced in migration comments

### Roles/GRANTs Applied
- [ ] `app_rw` role has appropriate grants
- [ ] `app_ro` role has appropriate grants
- [ ] `app_admin` role has appropriate grants (if applicable)
- [ ] Grants follow least-privilege principle

### RLS Policies Applied
- [ ] RLS enabled on all multi-tenant tables
- [ ] `tenant_isolation_policy` created using template pattern
- [ ] Policy uses `current_setting('app.current_tenant_id')::UUID`
- [ ] RLS policy documented in comments

### Comments Present on All Objects
- [ ] `COMMENT ON TABLE` for all tables (Purpose, Data Class, Ownership)
- [ ] `COMMENT ON COLUMN` for all columns (Purpose, Data Class)
- [ ] `COMMENT ON POLICY` for all RLS policies
- [ ] Comments follow minimum content requirements

### Migration Safety Checklist Reviewed
- [ ] Pre-migration checks completed (backup, timeouts)
- [ ] Post-migration checks planned (schema validation, index verification, RLS verification)
- [ ] Long-running operations use add-then-backfill-then-swap pattern (if applicable)
- [ ] Destructive changes approved (if applicable)

### Extension Allow-List Compliance
- [ ] No extensions used (or)
- [ ] Extension is in allow-list (`EXTENSION_ALLOWLIST.md`)
- [ ] Extension rationale documented
- [ ] Extension approved per environment policy

### Snapshot Drift Check Acknowledged
- [ ] Snapshot will be generated after migration
- [ ] Drift detection will be run
- [ ] Any drift will be resolved before merge

## Testing

- [ ] Migration tested locally
- [ ] Rollback tested (`alembic downgrade -1`)
- [ ] Dry-run reviewed (`alembic upgrade --sql head`)
- [ ] Multi-environment test completed (dev, test)

## Documentation

- [ ] Migration comments explain change and rationale
- [ ] Contract mapping documented (if applicable)
- [ ] Data dictionary will be updated (post-merge)
- [ ] ERD will be updated (post-merge)

## Approval

- [ ] Self-review completed
- [ ] Peer review completed
- [ ] Backend Lead approval (required)
- [ ] Product Owner approval (required for destructive changes)

---

**Reviewer Notes**: Add any additional comments or concerns here.

