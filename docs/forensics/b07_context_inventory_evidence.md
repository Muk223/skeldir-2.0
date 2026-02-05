# B0.7 Context Inventory — Evidence Pack (Forensic Baseline)

**Mode:** Forensic inventory only (no feature build, no new production code).

## 1) Audit Target + Environment Notes

### Audited `main` commit (source of truth)

- **Branch pinned:** `origin/main`
- **SHA:** `e234319a1ce9f499ad11ee1c7c80694bb8657d41`
- **Commit subject:** `Merge pull request #49 from Muk223/fix/r1-pyjwt-lock`

### Local environment (observed)

- OS shell: PowerShell (Windows)
- Python: `3.11.9`
- Alembic: `1.17.2`
- Docker CLI: `28.5.1` (daemon unavailable in this environment; details in Runtime Evidence)

### Workspace hygiene note

This audit intentionally **hard-reset local `main` to `origin/main`** (to avoid local drift) and stashed prior local changes. The evidence below is scoped to the audited SHA above.

---

## 2) Repo Map (B0.7-Relevant Modules / Seams)

### Database / schema / migrations

- Alembic config + env: `alembic.ini`, `alembic/env.py`
- Migrations (version locations): `alembic/versions/*`
  - LLM namespace: `alembic/versions/004_llm_subsystem/`
  - Celery foundation: `alembic/versions/006_celery_foundation/`
  - Grants/foundation: `alembic/versions/007_skeldir_foundation/`
- Canonical schema snapshot: `db/schema/canonical_schema.sql` (note: does **not** include every later migration artifact; see findings)

### Backend runtime (FastAPI + Celery)

- API entrypoint / router wiring: `backend/app/main.py`
- API routers (implemented): `backend/app/api/*` (no LLM router present)
- Settings + env loading: `backend/app/core/config.py`, `.env.example`
- DB session + tenant GUC injection (RLS contract): `backend/app/db/session.py`, `backend/app/db/deps.py`
- Auth context (tenant extraction): `backend/app/security/auth.py`
- Celery app init + queue routing: `backend/app/celery_app.py`, `backend/app/core/queues.py`
- Task tenant context decorator: `backend/app/tasks/context.py`

### LLM foundation (present in `main`)

- Budget policy engine (cap/fallback/block) + audit sink (`llm_call_audit`): `backend/app/llm/budget_policy.py`
- LLM tasks (Celery task stubs): `backend/app/tasks/llm.py`
- LLM worker implementations (DB audit writes, *no provider calls*): `backend/app/workers/llm.py`
- Canonical LLM task payload contract: `backend/app/schemas/llm_payloads.py`
- Canonical enqueue entrypoint: `backend/app/services/llm_dispatch.py`
- ORM models (LLM audit + jobs): `backend/app/models/llm.py`

### Infra definitions (local/compose)

- Compose files: `docker-compose.component-dev.yml`, `docker-compose.e2e.yml`, `docker-compose.mock.yml`, `docker-compose.yml.deprecated`
- Monitoring scaffolding (configs exist, not wired to compose here): `monitoring/prometheus/*`, `monitoring/grafana/*`

---

## 3) Hypothesis Adjudication Table

Status values: **VALIDATED**, **REFUTED**, **UNTESTABLE-LOCALLY**.

### A) Schema + Migration Ground Truth

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| H01 | VALIDATED | LLM migration namespace exists as `alembic/versions/004_llm_subsystem/`. | Directory listing; `alembic.ini` `version_locations`; `alembic/versions/004_llm_subsystem/*` |
| H02 | UNTESTABLE-LOCALLY | Clean-DB **apply** could not be executed here because Docker daemon is unavailable and no local Postgres was proven reachable. Offline SQL generation succeeded with UTF-8 settings. | Runtime: `docker info` error; Offline: `python -m alembic ... upgrade head --sql` succeeded (see Runtime Evidence) |
| H03 | REFUTED | `llm_api_calls` exists but **does not include `user_id` nor provider**. Actual cols: `tenant_id`, `created_at`, `endpoint`, `model`, `request_id`, `input_tokens`, `output_tokens`, `cost_cents`, `latency_ms`, `was_cached`, `request_metadata`. | Create table: `alembic/versions/004_llm_subsystem/202512081500_create_llm_tables.py:53-66`; Add `request_id` + unique: `alembic/versions/004_llm_subsystem/202601131610_add_llm_api_call_idempotency.py:19-46`; ORM: `backend/app/models/llm.py:27-71` |
| H04 | VALIDATED | `llm_monthly_costs` exists as a per-tenant per-month rollup. It can support *tenant-level* cap enforcement; **not per-user**. | Migration: `alembic/versions/004_llm_subsystem/202512081500_create_llm_tables.py:88-99`; ORM: `backend/app/models/llm.py:74-106` |
| H05 | REFUTED | No `distillation_eligible` field/table found in repo. | `rg distillation_eligible` yielded no matches (static scan) |
| H06 | REFUTED | LLM Celery tasks exist and write to LLM tables; there is no explicit runtime guard preventing enqueue/execution before migrations. (If schema missing, tasks fail at runtime.) | LLM tasks exist: `backend/app/tasks/llm.py`; writes: `backend/app/workers/llm.py` |

### B) RLS + Identity Contract

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| H07 | VALIDATED | RLS is enabled + **FORCED** on the 7 LLM subsystem tables. | `alembic/versions/004_llm_subsystem/202512081510_add_llm_rls_policies.py:63-81` |
| H08 | REFUTED | Policies isolate by **tenant only** (`app.current_tenant_id` GUC). No user-level RLS dimension is present. | `alembic/versions/004_llm_subsystem/202512081510_add_llm_rls_policies.py:71-75`; DB tenant GUC set: `backend/app/db/session.py:96-103`; no `app.current_user_id` usage (static scan) |
| H09 | VALIDATED | Tenant identity context injection is implemented in runtime DB/session and is used by API + workers. | API DB dep uses tenant: `backend/app/db/deps.py:13-23`; session sets GUC: `backend/app/db/session.py:86-110`; workers set GUC: `backend/app/tasks/context.py:104-156` |

### C) Provider Architecture (aisuite + wrapper)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| H10 | REFUTED | `aisuite` dependency/use is absent. | `rg \\baisuite\\b` yielded no matches (static scan) |
| H11 | REFUTED | No provider wrapper boundary (e.g. `SkeldirLLMProvider`) exists. Present: budget policy engine + deterministic worker stubs only. | LLM module contents: `backend/app/llm/*`; workers explicitly “never call providers”: `backend/app/workers/llm.py:1-5` |
| H12 | REFUTED | No config-driven provider selection is implemented (no provider dispatch exists). | No provider code; no `OPENAI`/`ANTHROPIC` settings; `aisuite` absent |

### D) Single Write Path + Telemetry Separation

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| H13 | VALIDATED | Exactly one production write site to `llm_api_calls` exists: `backend/app/workers/llm.py` (`insert(LLMApiCall)`). | Write-site scan: `backend/app/workers/llm.py:69-118` + repo-wide `rg` results (no other prod inserts) |
| H14 | REFUTED | No explicit `distillation_eligible` or training-signal gate exists; schema separation exists by table, but eligibility is not persisted as a correctness gate. | No `distillation_eligible` anywhere; schema tables: `alembic/versions/004_llm_subsystem/202512081500_create_llm_tables.py` |
| H15 | REFUTED | No reasoning trace capture/storage demarcation found. | No “reasoning trace” fields or modules found in `backend/app/` (static scan) |

### E) Cost Controls (Margin Protection)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| H16 | REFUTED | No `$25/user/month` hard cap enforcement exists. Present: **per-investigation** cap default `$0.30` policy engine (not wired to provider calls). | Budget policy cap default: `backend/app/llm/budget_policy.py:95-108`; no monthly cap logic found |
| H17 | REFUTED | No hourly emergency shutoff exists. | No matches for “emergency”/“shutoff” in backend runtime (static scan) |
| H18 | REFUTED | No provider invocation boundary exists; hard timeouts are only present as Celery task time limits (general), not LLM-call-level enforcement. | Celery task time limits config: `backend/app/core/config.py` (Celery time limit fields); no provider calls in `backend/app/workers/llm.py` |
| H19 | REFUTED | No “3 failures → open” breaker exists for LLM. (A cooldown pattern exists elsewhere for realtime revenue, not LLM.) | Cooldown in revenue cache: `backend/app/services/realtime_revenue_cache.py`; no LLM breaker module found |
| H20 | VALIDATED | LLM task retries are bounded (max_retries=3) and retry is conditional (`retry_on_failure`). | `backend/app/tasks/llm.py:76-135` (route) + similar for others; `backend/app/tasks/llm.py:137+` |

### F) Caching Posture (Resolve Contradiction in Reality)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| H21A | REFUTED | Redis is not present as runnable infra in compose; references are gated to docs/evidence only. | Postgres-only guard: `scripts/ci/enforce_postgres_only.py:9-79`; compose contains no redis service |
| H21B | VALIDATED | Postgres-only posture is enforced; “cache” tables exist (e.g., `explanation_cache`, `revenue_cache_entries`). LLM semantic cache has schema but no runtime use found. | LLM cache table exists: `alembic/versions/004_llm_subsystem/202512081500_create_llm_tables.py:173-195`; realtime cache code exists: `backend/app/services/realtime_revenue_cache.py` |
| H22 | REFUTED | No deterministic invalidation via `last_updated_at`/revision watermark was found for LLM cache keying. | `explanation_cache` schema lacks watermark; no usage in code (`rg explanation_cache` only hits migrations) |

### G) Observability Posture (Single Sink, No Drift)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| H23A | UNTESTABLE-LOCALLY | Prometheus/Grafana configs exist in-repo, but no local runtime proof was possible here (Docker daemon unavailable). | `monitoring/prometheus/*`, `monitoring/grafana/*`; Docker failure in Runtime Evidence |
| H23B | REFUTED | InfluxDB is not present (no code or infra definitions found). | `rg influx|influxdb` returned no matches (static scan) |
| H23C | VALIDATED | Postgres ledger tables exist for LLM usage/cost (`llm_api_calls`, `llm_monthly_costs`, `llm_call_audit`), and no alternate “truth store” was found. | Migrations: `alembic/versions/004_llm_subsystem/*`, `alembic/versions/003_data_governance/202512231010_add_llm_call_audit.py` |
| H24 | VALIDATED | No dual-sink cost/usage “truth” storage was found in code/infra. | Static scans for influx/redis; LLM writes go to Postgres tables only |

### H) Exposure Control (No Public Contract in B0.7)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| H25 | VALIDATED | No FastAPI routes expose LLM features; only auth/attribution/platforms/revenue/health/webhooks are included. | Router wiring: `backend/app/main.py:64-71`; API dir has no LLM module: `backend/app/api/*` |
| H26 | VALIDATED | No synchronous unbounded public “chat-like” route exists in backend routing. | Route inventory via `backend/app/main.py` + `backend/app/api/*` |

### I) Worker Stub + Queue Topology (Air-Gap Prevention)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| HW01 | VALIDATED | Celery app entrypoint is identifiable (`backend/app/celery_app.py`). | `backend/app/celery_app.py` |
| HW02 | VALIDATED | Queue topology and routing rules are defined (including `llm` queue and `app.tasks.llm.*` routes). | `backend/app/core/queues.py:8-20`; `backend/app/celery_app.py:150-222` |
| HW03 | VALIDATED | Task conventions exist: tenant-scoped decorator sets GUC + correlation; retries bounded; idempotency via request_id + unique constraint. | Tenant decorator: `backend/app/tasks/context.py:104-156`; LLM tasks: `backend/app/tasks/llm.py`; unique constraint: `alembic/versions/004_llm_subsystem/202601131610_add_llm_api_call_idempotency.py:42-46`; claim logic: `backend/app/workers/llm.py:69-118` |
| HW04 | VALIDATED | LLM task stubs exist (`route`, `explanation`, `investigation`, `budget_optimization`). | `backend/app/tasks/llm.py` task definitions |
| HW05 | VALIDATED | Worker-side tenant context injection supports RLS via `app.current_tenant_id` and sets execution_context=`worker`. | `backend/app/tasks/context.py:80-102` |
| HW06 | UNTESTABLE-LOCALLY | Could not prove broker connectivity + enqueue/consume end-to-end because no Postgres broker was started (Docker daemon unavailable; local Postgres not proven). | Runtime Evidence: Docker daemon error; no DB endpoint validated |

### J) Secrets + Config Injection (Anti-Hack Gate)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| HS01 | VALIDATED | Local dev `.env` loading exists via `python-dotenv` (skipped in CI). | `backend/app/core/config.py:15-19`; `backend/requirements-lock.txt:40`; `.env.example` |
| HS02 | VALIDATED | Compose injects required env vars (DB + auth + platform keys) for e2e stack. | `docker-compose.e2e.yml:36-56`; `docker-compose.component-dev.yml:8-120` |
| HS03 | VALIDATED | CI/e2e paths do not require real LLM provider keys because there is no provider integration. | No provider keys in settings; LLM workers stubbed (`backend/app/workers/llm.py:1-5`) |
| HS04 | REFUTED | No general log secret-redaction filter is present; structured logging emits JSON but does not redact. Repo also contains hardcoded DB URLs in non-runtime scripts (risk). | Logging formatter: `backend/app/observability/logging_config.py:17-40`; hardcoded DSN hits in `backend/*.py` (see Risks) |
| HS05 | REFUTED | Settings validate some required config (e.g. `DATABASE_URL` required; JWT must be configured to auth), but no LLM-secret validation exists yet. | DB required: `backend/app/core/config.py:30-36`; JWT guard: `backend/app/security/auth.py:52-67`; no LLM settings exist |

### K) Infrastructure Realizability (“Imports aren’t infra”)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| HI01 | VALIDATED | Redis is not runnable from repo compose; Postgres-only is enforced. | `scripts/ci/enforce_postgres_only.py`; compose files lack redis |
| HI02 | VALIDATED | Influx/Grafana via Influx is not runnable; Influx is absent. | `rg influx` no matches |
| HI03 | VALIDATED | Postgres-native structures for caching + rollups exist (realtime revenue cache tables/code; LLM cache + rollup tables in schema). | `backend/app/services/realtime_revenue_cache.py`; LLM tables in `alembic/versions/004_llm_subsystem/202512081500_create_llm_tables.py` |

### L) Topographical Insertion Map (Where Missing Things Must Land)

| ID | Status | Reality | Evidence |
|---:|:--|:--|:--|
| HT01 | VALIDATED | Canonical invocation boundary for future provider calls is the LLM worker layer (`backend/app/workers/llm.py`) called by Celery tasks (`backend/app/tasks/llm.py`). | Tasks call workers: `backend/app/tasks/llm.py:13-23`; workers stubbed: `backend/app/workers/llm.py` |
| HT02 | VALIDATED | Canonical persistence boundary for `llm_api_calls` + rollups is centralized in `backend/app/workers/llm.py` (`_claim_api_call`, `record_monthly_costs`). | `backend/app/workers/llm.py:69-182` |
| HT03 | VALIDATED | Central enforcement point for timeout/breaker/budget must be inside the (currently-missing) provider wrapper that workers would call (so it’s not duplicated across tasks). | Absence of provider wrapper; existing single worker callsite pattern |
| HT04 | VALIDATED | Cache boundary location is indicated by existing Postgres cache pattern (`backend/app/services/realtime_revenue_cache.py`) + presence of `explanation_cache` table. | Cache pattern: `backend/app/services/realtime_revenue_cache.py`; schema: `alembic/versions/004_llm_subsystem/202512081500_create_llm_tables.py:173-195` |
| HT05 | VALIDATED | Worker boundary is explicit: `backend/app/tasks/llm.py` (task wrappers) + `backend/app/workers/llm.py` (core execution). | `backend/app/tasks/llm.py`; `backend/app/workers/llm.py` |
| HT06 | VALIDATED | Config/secrets boundary is `backend/app/core/config.py` (Pydantic settings + dotenv), and compose files demonstrate env injection patterns. | `backend/app/core/config.py`; `docker-compose.*.yml` |

---

## 4) Static Evidence (Key Ground Truth)

### LLM tables (schema)

- `llm_api_calls` definition: `alembic/versions/004_llm_subsystem/202512081500_create_llm_tables.py:53-66`
- `llm_monthly_costs` definition: `alembic/versions/004_llm_subsystem/202512081500_create_llm_tables.py:88-99`
- RLS for LLM subsystem tables: `alembic/versions/004_llm_subsystem/202512081510_add_llm_rls_policies.py:63-81`
- LLM request idempotency + unique constraint: `alembic/versions/004_llm_subsystem/202601131610_add_llm_api_call_idempotency.py:19-46`
- Runtime role GRANTs for audit persistence: `alembic/versions/007_skeldir_foundation/202601221200_b057_p4_llm_audit_grants.py:23-35`

### LLM runtime write paths (prove uniqueness)

- `llm_api_calls` insert (single production site): `backend/app/workers/llm.py:69-118`
- `llm_monthly_costs` upsert (single production site): `backend/app/workers/llm.py:121-182` (insert at ~157)
- `llm_call_audit` insert (budget policy audit sink): `backend/app/llm/budget_policy.py:318-359`

### LLM tasks + payload contract

- Payload contract: `backend/app/schemas/llm_payloads.py:15-26`
- Canonical enqueue entrypoint: `backend/app/services/llm_dispatch.py:16-41`
- LLM tasks (bounded retries): `backend/app/tasks/llm.py:76-135` (+ other tasks below)
- Task tenant context injection: `backend/app/tasks/context.py:104-156`

### Public API exposure (or lack thereof)

- Implemented routers wired into FastAPI: `backend/app/main.py:64-71`
- API router modules present (no LLM): `backend/app/api/*`
- LLM OpenAPI contracts exist but appear served by mocks, not backend implementation: `api-contracts/openapi/v1/llm-*.yaml`, `api-contracts/dist/openapi/v1/llm-*.bundled.yaml`, and prism mock references in `Procfile` (see Risks/Gaps).

### Provider normalization dependency (aisuite)

- `aisuite` absent: no references in repo (`rg \\baisuite\\b` found none).

---

## 5) Runtime Evidence (Commands + Outputs)

### B1 — Apply migrations on a clean DB (blocked)

Attempt to start Postgres via compose:

```powershell
docker compose -f docker-compose.e2e.yml up -d postgres
```

Observed output (daemon unavailable):

```
unable to get image 'postgres:15-alpine': error during connect: ... open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

Docker daemon status proof:

```powershell
docker info
```

Observed output tail:

```
Server:
error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/info": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

Offline determinism check (static SQL generation) succeeded with UTF-8 env settings:

```powershell
$env:MIGRATION_DATABASE_URL='postgresql://migration_role:password@localhost:5432/skeldir_validation'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python -m alembic -c alembic.ini upgrade head --sql > .tmp\b07_alembic_upgrade_head.sql
echo "exit=$LASTEXITCODE"
```

Observed output:

```
exit=0
INFO  [alembic.runtime.migration] Generating static SQL
INFO  [alembic.runtime.migration] Running upgrade ... -> 202512081500, Add LLM subsystem tables ...
INFO  [alembic.runtime.migration] Running upgrade ... -> 202601131610, Add llm_api_calls idempotency key
...
```

### B2 — Worker bring-up check (blocked)

Blocked for the same reason as B1: worker requires Postgres broker/backend (`sqla+postgresql://`, `db+postgresql://`), but no local Postgres instance was started/proven reachable here.

---

## 6) Queue Topology Truth Table (From Code)

### Queue routing (global)

Defined queues: `housekeeping`, `maintenance`, `llm`, `attribution`.

- Source of truth: `backend/app/core/queues.py:8-20`
- Celery routing rules: `backend/app/celery_app.py:150-222`

### LLM queue tasks (B0.7-relevant)

| Queue | Task name | Payload type | Idempotency mechanism | Retry policy |
|:--|:--|:--|:--|:--|
| `llm` | `app.tasks.llm.route` | `LLMTaskPayload` from kwargs (`payload` dict + tenant/correlation/request/max_cost) | `llm_api_calls` unique on (`tenant_id`,`request_id`,`endpoint`) + `on_conflict_do_nothing` claim | `max_retries=3`, `default_retry_delay=30`, optional `retry_on_failure` gate |
| `llm` | `app.tasks.llm.explanation` | same | same | same |
| `llm` | `app.tasks.llm.investigation` | same | same | same |
| `llm` | `app.tasks.llm.budget_optimization` | same | same | same |

Evidence:

- Task declarations: `backend/app/tasks/llm.py:76-311`
- Payload contract: `backend/app/schemas/llm_payloads.py:15-26`
- Claim + idempotency: `backend/app/workers/llm.py:69-118`
- Unique constraint migration: `alembic/versions/004_llm_subsystem/202601131610_add_llm_api_call_idempotency.py:42-46`

---

## 7) Secrets Matrix (Local / Compose / CI)

| Surface | Injection method | Required keys (observed) | Failure mode (observed) | Evidence |
|:--|:--|:--|:--|:--|
| Local dev | `.env` loaded via `python-dotenv` unless `CI=true` | `DATABASE_URL` required; auth/platform keys optional depending on endpoints used | Settings load fails if `DATABASE_URL` missing; auth fails if JWT validation not configured | `backend/app/core/config.py:15-36`; `backend/app/security/auth.py:52-67` |
| Compose (component dev) | Env vars in compose | DB creds; webhook secrets; JWT secret placeholders | N/A (not executed here) | `docker-compose.component-dev.yml:8-120` |
| Compose (e2e) | Env vars in compose | `DATABASE_URL` + JWT + platform encryption keys for tests | N/A (not executed here) | `docker-compose.e2e.yml:36-56` |
| CI | Env vars in runner / compose for e2e | Same as e2e; no LLM provider keys required currently | N/A | No provider integration; stubs only |

---

## 8) Contradiction Resolution Outcomes

### Redis posture (Redis vs Postgres-only)

**Adjudicated reality:** **Postgres-only is enforced**; Redis is treated as prohibited except in an explicit allowlist of docs/evidence.

- CI guardrail rejects Redis references outside allowlist: `scripts/ci/enforce_postgres_only.py:9-79`
- Compose files define Postgres only; no Redis service: `docker-compose.component-dev.yml`, `docker-compose.e2e.yml`

### Telemetry sink posture (Prometheus vs Influx vs Postgres ledger)

**Adjudicated reality:** Influx is absent. Prometheus/Grafana config exists but runtime proof is untestable here. **Postgres is the canonical cost ledger** for LLM audit/rollups.

- Influx absent (`rg influx` no hits)
- Postgres ledgers exist: `llm_api_calls`, `llm_monthly_costs`, `llm_call_audit` (migrations listed above)

---

## 9) Gap List (What B0.7 Must Build Next)

1. **Provider wrapper boundary** (e.g., `SkeldirLLMProvider`) that owns: caching, cost tracking, timeouts, breaker, and single write path — currently absent.
2. **Provider normalization dependency** (`aisuite`) — currently absent.
3. **Hard margin controls**:
   - `$25 / user / month` hard cap (block) — absent; only per-investigation `$0.30` policy exists.
   - Hourly emergency shutoff — absent.
4. **Semantic caching implementation**:
   - `explanation_cache` table exists but is unused in runtime.
   - No LLM semantic cache invalidation watermark scheme.
5. **Training signal gating**:
   - No `distillation_eligible` persisted correctness gate.
   - No explicit separation/demarcation for reasoning traces vs final output.
6. **Observability for LLM calls**:
   - No LLM-specific metrics emission found.
   - Need structured logs/spans around future provider calls + budget decisions.
7. **RLS coverage gaps**:
   - `llm_call_audit` migration does not enable/force RLS (as written).
   - No user-level isolation dimension exists (tenant-only).

---

## 10) Risk List (Air-Gaps, Secret Leakage, Unbounded Paths)

1. **Docker daemon unavailable in this environment** blocks local proof of migration apply + broker connectivity; if this reflects developer environments, B0.7 integration could drift without runtime validation.
2. **Hardcoded DB URLs in non-runtime scripts/tests** risk credential leakage if copied/logged; no general log redaction filter exists.
   - Evidence: `backend/*.py` contains `os.environ["DATABASE_URL"] = "postgresql://..."` (multiple files, e.g., `backend/check_role_rls_bypass.py:5`).
3. **Budget policy audit sink RLS**: `llm_call_audit` table creation does not apply RLS/force-RLS in its migration; tenant isolation would rely on external/later policy not evidenced in migrations here.
4. **Retries + future provider calls**: bounded retries exist, but once provider calls are introduced, retries can amplify cost unless budget gating is checked per-attempt and before dispatch.
5. **No provider boundary exists** today, so enforcement risks duplication when implementation begins.

---

## 11) Topographical Insertion Map (Canonical Landing Zones)

This section is **where** each missing B0.7 component must land to match current repo seams and minimize drift.

### Provider wrapper (mandatory)

- **Canonical location:** `backend/app/llm/` (new module, e.g., `provider.py`), invoked by `backend/app/workers/llm.py`.
- **Why canonical:** All LLM work currently funnels through Celery tasks → `backend/app/workers/llm.py` and is already the ledger write boundary.
- **Binding interfaces:**
  - Settings: `backend/app/core/config.py` (provider keys, budgets, timeouts, kill switches)
  - Persistence: `backend/app/workers/llm.py` (or extracted “single write path” module under `backend/app/llm/`)
  - Task layer: `backend/app/tasks/llm.py` (payload normalization + bounded retries)

### Single write path to `llm_api_calls`

- **Current canonical sink:** `backend/app/workers/llm.py` (`_claim_api_call`, `record_monthly_costs`)
- **Enforcement approach:** Provider wrapper must call into this sink exactly once per logical request (idempotent via unique constraint).

### Cost controls (monthly cap + emergency shutoff)

- **Canonical enforcement point:** provider wrapper **before** dispatch.
- **Data sources:**
  - `llm_monthly_costs` rollup (tenant/month) exists; per-user ledger does not.
  - `llm_call_audit` exists for per-call decisions but has no proven RLS.
- **Required schema evolution (pre-traffic):**
  - Per-user rollup table or expanded rollup dimensions if `$25/user/month` is non-negotiable.
  - Explicit emergency shutoff state storage (tenant/user scoped) with TTL/hourly reset semantics.

### Circuit breaker + timeouts

- **Canonical location:** provider wrapper (central, non-duplicated).
- **Reuse pattern:** realtime revenue has deterministic cooldown + `Retry-After` semantics (see `backend/app/services/realtime_revenue_cache.py`); adapt pattern for LLM provider degradation.

### Semantic caching

- **Schema present:** `explanation_cache` (LLM explanations) and Postgres cache patterns exist.
- **Canonical cache boundary:** a new LLM cache module should mirror the established Postgres cache pattern (`backend/app/services/realtime_revenue_cache.py`) and write to LLM cache tables.
- **Invalidation boundary:** must be explicit (revision watermark or `last_updated_at` in cache key inputs); currently absent.

### Worker wiring (avoid air-gap)

- **Canonical path:** `backend/app/services/llm_dispatch.py` → `backend/app/tasks/llm.py` → `backend/app/workers/llm.py`.
- **Why:** This is already the “API-equivalent” enqueue entrypoint and keeps LLM work async (Centaur posture).
