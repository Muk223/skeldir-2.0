# Migration Policy Runbook

**Version:** 1.0.0  
**Date:** 2025-11-17  
**Status:** Operational Policy  
**Related Document:** `docs/database/REMEDIATION-B0.3-GOVERNANCE-SYSTEM-DESIGN.md`

---

## Purpose

This runbook codifies the **human** side of schema change governance. It defines policies, procedures, and exceptions for migration authoring, review, and deployment.

---

## Policy 1: Downgrade Governance

### Policy Statement

`alembic downgrade` is a **development-only tool**. Downgrades are **explicitly forbidden** in Staging or Production environments.

### Rationale

- Production data cannot be safely rolled back without data loss
- Downgrade functions are mechanical reversals that drop columns/tables
- Production schema errors must be fixed via forward-only remediation migrations

### Procedures

**Development Environment**:
- ✅ Downgrades allowed for testing migration rollback paths
- ✅ Use `alembic downgrade -1` to test single-migration rollback
- ✅ Verify schema returns to baseline state after downgrade/upgrade cycle

**Staging Environment**:
- ❌ Downgrades **forbidden**
- ✅ Schema errors fixed via new forward-only migration
- ✅ Emergency fixes follow emergency change process (see Policy 4)

**Production Environment**:
- ❌ Downgrades **strictly forbidden**
- ✅ All production schema errors fixed via forward-only remediation migration
- ✅ Rollback via separate migration or operational runbook (see Forward-Only Rollback)

### Enforcement

- CI/CD pipelines must not execute `alembic downgrade` in staging/production
- Database access controls should prevent downgrade execution in production
- Migration authors must document rollback strategy even for forward-only migrations

---

## Policy 2: Destructive Migration Approval

### Policy Statement

Any PR containing a destructive migration **must** link to an approved architecture review in its bypass comment.

### Destructive Operations

The following operations are considered **destructive**:
- `DROP TABLE`
- `DROP COLUMN`
- `DROP CONSTRAINT` (on critical constraints)
- `DROP INDEX` (on P0 query indexes)
- `ALTER TABLE ... DROP ...`
- `TRUNCATE TABLE`

### Bypass Comment Format

```python
op.drop_table('deprecated_table')  # CI:DESTRUCTIVE_OK - See ADR-015 for deprecation timeline
```

**Required Elements**:
- `# CI:DESTRUCTIVE_OK` comment on the same line as destructive operation
- ADR reference (e.g., `ADR-015`) or architecture review ticket
- Brief justification

### Approval Process

1. **Create ADR** or architecture review ticket documenting:
   - Why destructive operation is necessary
   - Impact assessment (data loss, downtime, etc.)
   - Rollback plan (if applicable)

2. **Get Architecture Review Approval**:
   - Technical Lead approval required
   - Data Platform Partner approval (if data loss)
   - SRE approval (if downtime risk)

3. **Add Bypass Comment**:
   - Include ADR/ticket reference in migration file
   - CI will pass validation with proper bypass comment

### Enforcement

- CI job `validate-migrations` checks for bypass comments
- PR reviewers must verify ADR exists and is approved
- Migration authors must not merge without approval

---

## Policy 3: Forward-Only Migration Policy

### Policy Statement

All production schema errors **must** be fixed via a **new, forward-only** remediation migration.

### Forward-Only Migration Requirements

When creating a forward-only migration:

1. **Mark in Metadata**:
   ```python
   """
   Migration Metadata
   
   FORWARD_ONLY: Yes
   JUSTIFICATION: <explanation of why downgrade is impossible>
   """
   ```

2. **Provide Rollback Plan**:
   - Document separate migration for rollback (if possible)
   - Or document operational runbook for manual rollback
   - Or document that rollback requires data loss (with approval)

3. **Require Stronger Review**:
   - Architecture review required
   - Technical Lead approval required
   - Data Platform Partner approval (if data loss)

### Forward-Only Rollback Strategies

**Strategy 1: Separate Rollback Migration**
- Create new migration that reverses changes
- Example: Drop column added in forward-only migration

**Strategy 2: Operational Runbook**
- Document manual SQL commands for rollback
- Example: Restore table from backup, then reapply safe migrations

**Strategy 3: Data Loss Acceptable**
- Document that rollback requires data loss
- Get explicit approval from stakeholders
- Example: Cannot rollback data transformation without losing transformed data

### Example Forward-Only Migration

```python
"""
Migration Metadata

MIGRATION_ID: 202511180000
TITLE: Backfill idempotency_key from external_event_id (irreversible)
CHANGE_TYPE: Column
RISK_LEVEL: Medium
FORWARD_ONLY: Yes
JUSTIFICATION: This migration backfills idempotency_key from external_event_id using COALESCE. The transformation is one-way because external_event_id may be NULL for some rows, making reverse mapping impossible.
ROLLBACK_STRATEGY: Separate migration required to drop idempotency_key column (data loss acceptable per ADR-012). See docs/database/RUNBOOK-MIGRATION-POLICY.md §Forward-Only Rollback.
"""
```

---

## Policy 4: Emergency Change Process

### Policy Statement

Emergency schema changes (production incidents) follow a **retroactive** change-control process.

### Emergency Change Procedure

1. **Immediate Action**:
   - Apply emergency fix directly to production (if necessary)
   - Document action taken in incident ticket

2. **Within 24 Hours**:
   - Create retroactive migration reflecting emergency change
   - Update canonical spec to match production state
   - Run validator against production to confirm alignment

3. **Post-Incident Review**:
   - Document in `db/schema/EXCEPTIONS.md`
   - Create ADR if emergency pattern should become standard
   - Review access controls to prevent future emergencies

### Emergency Change Documentation

```markdown
## Emergency Change: <Date>

**Incident**: [Incident ticket]  
**Urgency**: CRITICAL (production down)

## Immediate Action Taken

[Describe schema change applied in production]

## Retroactive Canonical Spec Update

[PR link updating canonical spec to reflect emergency change]

## Post-Incident Review

[Link to post-mortem]
```

### Emergency Validation

**Within 24 hours of emergency change**:
1. Update canonical spec to match production
2. Run validator against production
3. Confirm exit code = 0 (no divergences)
4. Document in EXCEPTIONS.md

**No Emergency Override for**:
- Feature requests (can wait for normal process)
- Performance optimizations (can wait)
- "Nice to have" changes

---

## Policy 5: Migration Authoring Standards

### Single-Purpose Rule

Each migration must be **logically small** and **single-purpose**. Avoid multi-unrelated changes in one migration.

**Good Example**:
```python
# Migration: Add idempotency_key column
def upgrade():
    op.add_column('attribution_events', sa.Column('idempotency_key', sa.String(255)))
```

**Bad Example**:
```python
# Migration: Add idempotency_key AND create new table AND add index
def upgrade():
    op.add_column('attribution_events', sa.Column('idempotency_key', sa.String(255)))
    op.create_table('new_table', ...)
    op.create_index('idx_new', ...)
```

### Metadata Completion

Every migration must include complete metadata header (see `REMEDIATION-B0.3-GOVERNANCE-SYSTEM-DESIGN.md` §2.1).

### Rollback Strategy Documentation

Even forward-only migrations must document rollback strategy (see Policy 3).

---

## Policy 6: Review Requirements

### Risk-Based Review

**Low Risk** (Standard PR + CI):
- Add non-nullable column with default
- Add index
- Add matview
- Add RLS policy consistent with existing contract

**Medium Risk** (PR + CI + Backend Lead Review):
- Add column without default to large table
- Add FK constraint
- Add new table used by ingestion

**High Risk** (PR + CI + Architecture Review + Documented Rationale):
- Drop column
- Drop table
- Change column type to narrower domain
- Drop/modify RLS
- Drop index used by P0 queries
- Changes affecting privacy/retention constraints

### Review Checklist

PR reviewers must verify:
- [ ] Migration metadata header is complete
- [ ] Risk level matches change type
- [ ] B0.3 domain flags (`TOUCHES_*`) are accurate
- [ ] B0.3 doc references are present (if `TOUCHES_* = Yes`)
- [ ] Destructive operations have bypass comments with ADR reference
- [ ] Rollback strategy is documented
- [ ] CI checks pass (schema drift, safety gate, domain-aware checks)

---

## Policy 7: Out-of-Band Changes Prohibition

### Policy Statement

Direct SQL changes in prod/staging/local without migrations are **forbidden by policy**.

### Prohibited Patterns

❌ **Forbidden**:
- Manual `ALTER TABLE` in production
- Direct `CREATE INDEX` in staging
- Ad-hoc schema changes via database GUI tools
- Emergency fixes without retroactive migration (see Policy 4)

✅ **Allowed**:
- Migrations via Alembic
- Emergency fixes with retroactive migration (within 24 hours)
- Database maintenance (VACUUM, ANALYZE) - not schema changes

### Enforcement

- Database access controls should prevent schema changes outside migration system
- CI validates that all schema changes are represented as migrations
- Audits should detect unauthorized schema changes

---

## Related Documents

- **Implementation Document**: `docs/database/REMEDIATION-B0.3-GOVERNANCE-SYSTEM-DESIGN.md`
- **Change Control Process**: `db/schema/CHANGE_CONTROL.md`
- **B0.3 → B0.4 Contract**: `docs/handoffs/CONTRACT-B0.3_TO_B0.4.md`

---

**Document Status**: ✅ Complete  
**Next Review**: 2026-01-17 (quarterly review)




