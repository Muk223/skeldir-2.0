# AGENTS Ruleset (Universal: Claude / Cursor / Codex)

> This file is the single, model-agnostic source of truth. All `.cursor/rules.d/*.mdc`
> files only route Cursor auto-attach to these rules. Keep this document authoritative.

## About the User and Role
- User is an experienced senior backend/database engineer.
- Values “Slow is Fast”: correctness, architecture, maintainability over speed.
- Objective: deliver correct, PE-ready solutions with minimal interactions, honoring explicit constraints.

## Core Architectural Mandate
- Modular monolith with strict seams: ingestion, attribution, auth, webhooks, tasks.
- Deterministic core: Postgres + FastAPI/Pydantic + Celery (Postgres broker/backend); LLMs only explain/summarize deterministic outputs.
- Postgres-only data system: no Redis/Kafka/NoSQL; caching via ETag/materialized views.
- Privacy-first: no PII persistence; no identity stitching; session-scoped analytics; IP only for in-memory rate limiting.
- Contract-first: OpenAPI 3.1 before code; Pydantic models generated; Prism mocks; oasdiff for breaking changes.
- Observability-by-default: OpenTelemetry spans; structured JSON logs with tenant_id, correlation_id, event_type; metrics for ingestion/attribution/LLM usage.
- Centaur UX: async review-and-approve; no synchronous chat for financial/attribution decisions.
- Model preference: prioritize Claude 4.5 Opus for reasoning-heavy transforms (fallback to available models if unavailable).

## Endpoint Patterns
- Attribution API: prefix /api/attribution; require X-Correlation-ID (UUID); derive tenant_id via dependency; db via get_db(); ETag 30s; revenue stored as cents → dollars in responses; include tenant_id, last_updated, data_freshness_seconds; no PII; span + structured logs; generated Pydantic models only.
- Ingestion: idempotency key f"{tenant_id}:{event_id}"; channel normalization via app/ingestion/channel_normalization.normalize_channel(); dead letter for validation failures; ephemeral session_id (<=30m); PII stripped; structured logs with tenant_id/correlation_id/event_type=ingestion.
- Webhooks: validate HMAC/signatures (Shopify, WooCommerce, Stripe, PayPal); strip PII; ephemeral session_id; idempotency via transaction/order IDs; correlation_id from headers or generated; deterministic only.

## Data & Models
- Tenant-scoped: tenant_id UUID NOT NULL FK tenants(id) ON DELETE CASCADE.
- Monetary: revenue_cents INTEGER (no DECIMAL/FLOAT).
- Semi-structured: JSONB for raw payloads/metadata.
- RLS: ENABLE ROW LEVEL SECURITY + policy USING (tenant_id = current_setting('app.current_tenant_id')::UUID).
- Indexes: composite (tenant_id, timestamp DESC) for time-series.
- State where relevant: pending, processed, failed, dead.

## Background Tasks
- Celery broker/backend: db+postgresql:// only.
- Task names: app.tasks.{module}.{task_name}; propagate correlation_id in logs.
- Async via asyncio.run; retries with backoff; log failures with context.
- REFRESH MATERIALIZED VIEW CONCURRENTLY for view maintenance.

## Statistical Models
- Deterministic: first_touch, last_touch, linear, time_decay; 100% allocation completeness; 30-day default lookback.
- Bayesian: pymc-marketing; store model_type/version; run diagnostics.
- Convergence: R-hat < 1.01, ESS > 400, divergences == 0; store diagnostics; CI fails on violation.
- LLM boundary: LLMs never compute; they only explain deterministic/Bayesian outputs.

## LLM Governance (Centaur)
- Explanation/synthesis only; no financial/attribution calculations.
- Routing + semantic caching required; bounded agents: ≤60s, ≤10 tool calls, ≤$0.30/investigation.
- Output validation: Pydantic-validate and DB-cross-check numeric claims; reject/regenerate on mismatch; log model/cost/deltas.
- Cost/audit logging: log every call (user_id, feature, model, tokens, cost, latency, cache hit); monthly rollups; alert and downgrade when near budget.
- UX: async review-and-approve; no synchronous chat for decisions.

## Contracts and SDK
- OpenAPI in api-contracts/openapi/v1/ before implementation; semantic versioning (major=breaking).
- Require X-Correlation-ID on all endpoints; tenant_id in tenant-scoped responses.
- Generate Pydantic models via datamodel-codegen; keep Prism mocks in sync; run oasdiff breaking in CI.
- SDK: openapi-generator-cli → frontend/src/generated/api/; version aligned to API semver; regenerate on contract changes.

## Quality and Observability
- Lint/type/format: Ruff, mypy, black; cyclomatic complexity <10/function.
- Tests: business logic ≥80% coverage; statistical models ≥95%.
- Docstrings on public functions; attribution endpoints document statistical validation requirements.
- Spans + structured logs everywhere.

## Prohibitions
- No Redis/Kafka/NoSQL; no alternate Celery brokers.
- No revenue DECIMAL/FLOAT; use INTEGER cents.
- No endpoints without X-Correlation-ID; no tenant-scoped responses missing tenant_id.
- No missing RLS on tenant tables; no raw SQL bypassing ORM where models exist.
- No identity stitching/cross-device tracking; no PII storage.
- No LLMs doing calculations or returning unvalidated numbers.
- No synchronous chat UX for financial/attribution decisions.

## Quality Gates
- oasdiff breaking passes.
- RLS verified on new tenant tables.
- Coverage: ≥80% business logic, ≥95% statistical models; CI fails otherwise.
- Convergence checks enforced in tests.
- mypy clean.
- Deploy: major bump for breaking changes; migration guides; RLS enabled in prod; diagnostics pass in prod.

## Workflow Discipline
- Plan mode for moderate/complex tasks (read code first, state objectives/constraints, present options/trade-offs).
- Code mode for implementation (concrete changes, minimal surface, tests to verify).
- Call out high-risk/irreversible changes (migrations, public APIs); propose safer alternatives.
- Prefer reasoned assumptions over excessive questions; revise when new info arrives.
- Conflict resolution: correctness/safety → business needs → maintainability → performance → brevity.
- Testing: add/recommend tests for non-trivial changes; never claim tests were run.
- Style: English; PEP 8; comments only when intent is non-obvious (explain “why”).
- Self-check: fix obvious errors you introduce; avoid history-rewriting/destructive ops unless explicitly approved.

## Roadmap Alignment
- Early (B0.x): RLS schema, ingestion idempotency + channel normalization, contracts + mocks, Postgres Celery, interim realtime revenue (clearly unverified).
- B0.7+: LLM routing/caching/cost logging; define worker stubs early to avoid broker/queue churn.
- B1.x: JWT/RBAC, privacy enforcement, Centaur UX (async review/approve), LLM output validation, sub-500ms cached RAG endpoints.
- B2.x: Deterministic attribution, webhook revenue verification, reconciliation, convergence diagnostics, explanation layer over deterministic data.
- Evolution triggers: Re-evaluate architecture only if >10k customers OR >100M events/day OR >$10M ARR OR p50 latency >2s for 30+ days.

