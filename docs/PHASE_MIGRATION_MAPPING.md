# Phase Numbering System

**Reference Guide: Mapping Platform Phases to Migration Phases**

---

## Overview

SKELDIR 2.0 uses **two parallel numbering systems** that serve different purposes:

1. **Platform Phases (B0.x, B1.x, B2.x)**: Business/product development milestones
2. **Migration Phases (001, 002, 003)**: Database schema versioning via Alembic

This document explains the relationship and mapping between them.

---

## Platform Phases (B0.x, B1.x, B2.x)

**Purpose**: Track overall platform evolution and feature readiness

**Tracking**: Defined in [AGENTS.md](../AGENTS.md) and [db/GOVERNANCE_BASELINE_CHECKLIST.md](../db/GOVERNANCE_BASELINE_CHECKLIST.md)

**Current Phase**: B0.3 (Database Schema Foundation)

### Phase Definitions

| Phase | Name | Focus | Status |
|-------|------|-------|--------|
| **B0.1** | API Contract Definition | OpenAPI contracts + Prism mocks | ✅ Complete |
| **B0.2** | Frontend Infrastructure | React/Vite frontend + mock integration | ✅ Complete |
| **B0.3** | Database Governance Baseline | Schema design + RLS + immutability | 🔄 In Progress |
| **B0.4-B0.6** | Service Expansion | Ingestion, attribution, webhooks | ⏳ Planned |
| **B0.7+** | LLM Integration | Routing, caching, cost controls | ⏳ Planned |
| **B1.x** | Auth & Governance | JWT, RBAC, privacy enforcement | ⏳ Planned |
| **B2.x** | Statistical Attribution | Deterministic + Bayesian models | ⏳ Planned |

---

## Migration Phases (001, 002, 003)

**Purpose**: Version database schema changes using Alembic

**Location**: `alembic/versions/`

**Versioning**: Timestamp-based (e.g., `202511121302_baseline.py`)

**Organization**: Grouped into directories by migration phase

### Migration Directory Structure

```
alembic/versions/
├── 001_core_schema/              [5 migrations]
│   ├── 202511121302_baseline.py
│   ├── 202511131115_add_core_tables.py
│   ├── 202511131119_add_materialized_views.py
│   ├── 202511131120_add_rls_policies.py
│   └── 202511131121_add_grants.py
│
├── 002_pii_controls/             [2 migrations]
│   ├── 202511161200_add_pii_guardrail_triggers.py
│   └── 202511161210_add_pii_audit_table.py
│
└── 003_data_governance/          [23 migrations]
    ├── 202511131232_enhance_allocation_schema.py
    ├── 202511131240_add_sum_equality_validation.py
    ├── ... (20+ additional migrations)
    └── 202511171200_reconcile_b03_baseline.py
```

### Migration Phase Purposes

| Phase | Name | Delivered In | Purpose |
|-------|------|--------------|---------|
| **001** | Core Schema | B0.3 | Foundation tables (events, ledger, allocations), MVs, RLS setup |
| **002** | PII Controls | B0.3 + B1.x | Privacy enforcement (triggers, audit tables) |
| **003** | Data Governance | B0.3 | Channel taxonomy, revenue ledger structure, state management |

---

## Platform ↔ Migration Mapping

### Current Mapping (B0.1 - B0.3)

| Platform Phase | Status | Migration Phase(s) | What Gets Delivered | Evidence |
|---|---|---|---|---|
| **B0.1** | ✅ Complete | None (pre-migration) | API contracts in YAML, Prism mocks | [contracts/](../contracts/) directory |
| **B0.2** | ✅ Complete | None (no DB changes) | React frontend, mock integration | [frontend/](../frontend/) directory |
| **B0.3** | 🔄 In Progress | 001, 002, 003 | Database schema foundation, governance rules | [alembic/versions/](../alembic/versions/) |

### Future Mapping (B0.4+)

| Platform Phase | Status | Migration Phase(s) | Planned Focus |
|---|---|---|---|
| **B0.4-B0.6** | ⏳ Planned | 004, 005, 006 | Ingestion service tables, webhook schemas |
| **B0.7+** | ⏳ Planned | TBD | LLM service tables, cost tracking |
| **B1.x** | ⏳ Planned | 002 (enhanced) | Auth tables, RBAC policies |
| **B2.x** | ⏳ Planned | 007+ | Attribution model tables, results storage |

---

## Key Rules

### 1. Migrations Run in Order
```bash
alembic upgrade head  # Runs 001_*, then 002_*, then 003_* in timestamp order
```

### 2. Platform Phase Defines "When to Run"
- **B0.3**: Run migrations 001, 002, 003
- **B0.4**: Will run migrations 004, 005, etc.
- **B0.7**: May add migrations to 002 (PII phase) for new privacy controls

### 3. Multiple Platform Phases Can Use Same Migration Phase
Example: Both B0.3 and B1.x use migration phase 002 (PII controls) because:
- B0.3 delivers: Basic PII prevention (triggers)
- B1.x delivers: Advanced PII governance (RBAC-aware deletion)

### 4. Release Checklist Links Both
**Phase Gate Example (B0.3)**:
```markdown
## B0.3 Exit Gate Requirements

✓ All migrations in 001_core_schema/ have executed
✓ All migrations in 002_pii_controls/ have executed
✓ All migrations in 003_data_governance/ have executed
✓ RLS verified on new tables (see ACCEPTANCE_RULES.md)
✓ Schema validation passed (scripts/validate-schema-compliance.py)
```

---

## How to Check Current State

### "What platform phase are we in?"

Check: [db/GOVERNANCE_BASELINE_CHECKLIST.md](../db/GOVERNANCE_BASELINE_CHECKLIST.md)
```markdown
# B0.3 Governance Baseline Completion Checklist

- [x] Core tables created (001_*)
- [x] PII controls deployed (002_*)
- [x] Governance layer implemented (003_*)
```

### "What migrations have been run?"

```bash
cd backend
alembic current         # Shows current revision
alembic history         # Shows all applied migrations
```

### "What's the mapping for the next phase?"

Check this document + [AGENTS.md](../AGENTS.md) roadmap section

---

## Migration vs. Platform Phase Examples

### Example 1: Adding a Webhook Vendor (B0.4)

**Platform Phase**: B0.4 (Service Expansion)

**Migration Phase**: 004_webhook_schemas (hypothetical)

**What changes**:
- New migration adds webhook event tables
- New contract adds webhook spec
- Platform phase B0.4 is "complete" when:
  - All 004_* migrations executed
  - Webhook handler implemented
  - Tests pass
  - CI validation passes

---

### Example 2: Implementing Advanced PII Controls (B1.x)

**Platform Phase**: B1.x (Auth & Governance)

**Migration Phase**: 002 (PII Controls) — *enhanced*

**What changes**:
- New migration to 002_pii_controls/ adds RBAC-aware deletion
- Extends existing PII control infrastructure (not replacing it)
- Platform phase B1.x uses both B0.3 (basic) + new (advanced) PII controls

---

## Quick Reference

### For Backend Engineers

When implementing a feature:

1. **Check platform phase target**: [db/GOVERNANCE_BASELINE_CHECKLIST.md](../db/GOVERNANCE_BASELINE_CHECKLIST.md)
2. **Find associated migration phase**: This document
3. **Write migrations** in correct directory: `alembic/versions/00X_*/`
4. **Run locally**: `alembic upgrade head`
5. **Test**: `make schema-validate`

### For Product/Planning

When planning a release:

1. **Identify platform phase target**: B0.x, B1.x, etc.
2. **Find what migrations are needed**: This document
3. **Estimate migration effort**: Check affected migration phase size
4. **Check dependencies**: Earlier phases must complete first

### For DevOps/CI

When deploying:

1. **Identify target platform phase**: From release notes
2. **Verify migrations**: `alembic current` vs. target
3. **Execute migrations**: `alembic upgrade head`
4. **Validate schema**: Run `scripts/validate-schema-compliance.py`
5. **Post-deploy verification**: Check RLS, immutability, etc.

---

## Related Documentation

- **[AGENTS.md](../AGENTS.md)** - Full roadmap (sections: "Evolution triggers", "Roadmap Alignment")
- **[db/GOVERNANCE_BASELINE_CHECKLIST.md](../db/GOVERNANCE_BASELINE_CHECKLIST.md)** - Phase gate criteria
- **[db/schema/ACCEPTANCE_RULES.md](../db/schema/ACCEPTANCE_RULES.md)** - Table-by-table acceptance criteria
- **[alembic/versions/](../alembic/versions/)** - Actual migrations

---

**Last Updated**: 2025-12-07
**Maintained By**: Backend Engineering Lead
**Reference**: Alembic versioning + Phase gates
