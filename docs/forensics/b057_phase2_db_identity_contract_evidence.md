# B0.5.7-P2 — DB Identity Contract Evidence (Production-truth, Least Privilege)

**Objective**: Make the production-truth DB identity contract explicit and testable on the canonical topology (`docker-compose.e2e.yml`), proving:

- Runtime identity cannot directly access `public.tenants`.
- Required tenant resolution is mediated via a narrow DB interface (`SECURITY DEFINER`).
- `llm_api_calls` (and required LLM tables) are writable by runtime under RLS and fail closed without tenant context.
- The privilege state is deterministic (no manual GRANTs).

**Collected (local)**: `2026-01-21` (Windows, PowerShell, Docker Desktop)

**Git/CI anchors**
- Branch: `b057-p2-db-identity-contract`
- Commit (head): `108a9209034a0de401c70068a2bb3a5599e45106`
- CI run: https://github.com/Muk223/skeldir-2.0/actions/runs/21219344381

---

## G0 — Ground Truth Anchors

Canonical topology:
- `docker-compose.e2e.yml` provisions runtime login role `app_user` and grants membership in `app_rw` (if present).
- Alembic is executed as the DB superuser via `MIGRATION_DATABASE_URL` (`postgres` in the compose topology).

Runtime identities (compose truth):
- API/worker connect as `app_user` (`DATABASE_URL=postgresql+asyncpg://app_user:app_user@db:5432/skeldir_e2e`)
- `app_user ∈ app_rw` (role membership grant executed after migrations)

---

## EG-P2-1 — Baseline Failure Reproduction (Pre-P2 contract)

To avoid relying on stale docs, a **baseline DB** was created by running migrations only up to the pre-P2 revision:

- Baseline target revision: `202601131610`
- Baseline DB name: `skeldir_p2_baseline`

### Baseline privilege truth (before P2 remediation)

As superuser:
```sql
SELECT
  has_table_privilege('app_user','public.tenants','SELECT') AS app_user_select_tenants,
  has_table_privilege('app_user','public.llm_api_calls','INSERT') AS app_user_insert_llm_api_calls,
  has_table_privilege('app_user','public.llm_api_calls','SELECT') AS app_user_select_llm_api_calls;
```

Observed output:
```text
app_user_select_tenants = f
app_user_insert_llm_api_calls = f
app_user_select_llm_api_calls = f
```

As runtime (`app_user`), direct tenants read is denied:
```text
ERROR:  permission denied for table tenants
```

As runtime (`app_user`), `llm_api_calls` write is denied:
```text
ERROR:  permission denied for table llm_api_calls
```

This confirms the blocking deficiencies:
- H-P2-DEF-1: runtime cannot write `llm_api_calls`
- H-P2-DEF-2: runtime cannot read from `tenants` (and code paths attempted to)

---

## Remediation Summary (What changed)

### DB contract migration (deterministic)

Added Alembic migration:
- `alembic/versions/007_skeldir_foundation/202601211200_p2_db_identity_contract.py`

Key actions:
- Create privileged no-login definer role: `app_security` (`BYPASSRLS`, no membership grants).
- Enforce deny-by-default on `public.tenants` for runtime roles (`app_user`, `app_rw`, `PUBLIC`).
- Create dedicated schema `security` owned by `app_security`.
- Add narrow privileged interfaces (owned by `app_security`, `SECURITY DEFINER`, safe `search_path`):
  - `security.list_tenant_ids()`
  - `security.resolve_tenant_webhook_secrets(text)`
- Grant runtime role (`app_rw`) **EXECUTE** on those functions (and **no** direct table access to `tenants`).
- Grant runtime role (`app_rw`) only the required LLM table privileges:
  - `public.llm_api_calls`: `SELECT, INSERT`
  - `public.llm_monthly_costs`: `SELECT, INSERT, UPDATE`
  - `public.investigations`: `SELECT, INSERT`
  - `public.budget_optimization_jobs`: `SELECT, INSERT`

### Code paths updated to comply (no direct tenants reads)

- `backend/app/tasks/matviews.py`: replaced `SELECT id FROM tenants` with `SELECT tenant_id FROM security.list_tenant_ids()`.
- `backend/app/core/tenant_context.py`: replaced direct `FROM tenants` lookup with `FROM security.resolve_tenant_webhook_secrets(:api_key_hash)`.

---

## EG-P2-2 — Privilege Truth Table (Post-remediation)

| DB Object | Access | Required by | Runtime identity | Grant mechanism | RLS expectation |
| --- | --- | --- | --- | --- | --- |
| `public.tenants` | `SELECT` | (forbidden) | `app_user` | none (explicit `REVOKE`) | N/A (privilege denied) |
| `security.list_tenant_ids()` | `EXECUTE` | `backend/app/tasks/matviews.py` (`pulse_matviews_global`) | `app_user` (via `app_rw`) | `GRANT EXECUTE` | function-owned privileged read |
| `security.resolve_tenant_webhook_secrets(text)` | `EXECUTE` | `backend/app/core/tenant_context.py` (`get_tenant_with_webhook_secrets`) | `app_user` (via `app_rw`) | `GRANT EXECUTE` | function-owned privileged read |
| `public.llm_api_calls` | `INSERT/SELECT` | `backend/app/workers/llm.py` (`_claim_api_call`) | `app_user` (via `app_rw`) | table grants | RLS enforced on `tenant_id = current_setting(...)` |
| `public.llm_monthly_costs` | `INSERT/UPDATE/SELECT` | `backend/app/workers/llm.py` (`record_monthly_costs`) | `app_user` (via `app_rw`) | table grants | RLS enforced |
| `public.investigations` | `INSERT/SELECT` | `backend/app/workers/llm.py` (`run_investigation`) | `app_user` (via `app_rw`) | table grants | RLS enforced |
| `public.budget_optimization_jobs` | `INSERT/SELECT` | `backend/app/workers/llm.py` (`optimize_budget`) | `app_user` (via `app_rw`) | table grants | RLS enforced |

---

## EG-P2-3 / EG-P2-4 — Least Privilege Tests (Canonical DB)

New CI-grade integration tests:
- `backend/tests/integration/test_b057_p2_db_identity_contract.py`

Behavior proven (tests pass locally against `docker-compose.e2e.yml` DB):
- Runtime **cannot** `SELECT` from `public.tenants`.
- Runtime **can** execute `security.list_tenant_ids()` and `security.resolve_tenant_webhook_secrets(text)`.
- `llm_api_calls` is fail-closed without tenant context (RLS blocks insert).
- `llm_api_calls` insert succeeds after setting `app.current_tenant_id` to the row’s tenant.

---

## EG-P2-5 — CI Canonical Validation Gate

Added a dedicated workflow that boots canonical topology and runs the P2 tests:
- `.github/workflows/b057-p2-db-identity-contract.yml`

It uploads:
- compose logs/ps output
- pytest output
- a DB privilege probe (`has_table_privilege` / `has_function_privilege`) artifact

---

## EG-P2-6 — Ledger/Index

Index updated:
- `docs/forensics/INDEX.md` (new row for B0.5.7 Phase 2)
