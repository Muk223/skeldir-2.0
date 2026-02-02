# Phase 5 Context Delta Notes (B0.6)

Date: 2026-02-02
Repo: C:\Users\ayewhy\II SKELDIR II

## Step A — Identify canonical response builder(s)

Commands:
- Get-Content backend/app/api/attribution.py
- Get-Content backend/app/api/revenue.py
- Get-Content backend/app/services/realtime_revenue_cache.py

Findings:
- Attribution endpoint `backend/app/api/attribution.py:get_realtime_revenue` assembles the response inline (dict literal). It computes `data_freshness_seconds` locally using `datetime.now(...)`.
- V1 endpoint `backend/app/api/revenue.py:get_realtime_revenue_v1` assembles the response inline (dict literal) and returns `snapshot.data_as_of` without freshness.
- No shared response builder or service exists; both endpoints call `get_realtime_revenue_snapshot` and then build their own response payloads.

Conclusion:
- Response assembly is duplicated across endpoints; freshness and verified semantics are not centralized.

## Step B — Trace semantics across 4 paths

Commands:
- Get-Content backend/app/services/realtime_revenue_cache.py
- Get-Content backend/app/services/realtime_revenue_providers.py
- Get-Content backend/app/api/attribution.py

### Cache hit path
- Fetch time source: `realtime_revenue_cache.RealtimeRevenueSnapshot.from_payload` loads `data_as_of` from cached payload; if missing, it falls back to `_utcnow()`.
- `last_updated` / `data_as_of`: returned from snapshot payload (no mutation on cache hit).
- Freshness seconds: computed in `backend/app/api/attribution.py` using `datetime.now(...)` at request time.
- Verified: passed through from snapshot payload (not forced false).

### Leader refresh path
- Fetch time source: `realtime_revenue_providers._fetch_realtime_revenue_snapshot` uses `effective_now` (sanitized `now` or `_utcnow()`), and providers return `ProviderRevenueResult.data_as_of=ctx.now`.
- `data_as_of` is set to `max(result.data_as_of)` (effectively fetch completion time).
- Freshness seconds: computed at request time in attribution endpoint, not at fetch time.
- Verified: `RealtimeRevenueSnapshot` is created with `verified=False` in provider aggregator, but no canonical response lock exists.

### Follower wait path
- Fetch time source: follower reads `payload` from `revenue_cache_entries` and converts to `RealtimeRevenueSnapshot`.
- `data_as_of` is whatever leader stored in payload; no explicit follower override.
- Freshness seconds: computed in attribution endpoint using follower-local `datetime.now(...)`.
- Verified: passed through from payload (not explicitly locked).

### Failure / cooldown path
- On fetch failure, `_record_failure` writes `payload` and `data_as_of` using `now` if no existing payload, and uses `existing_data_as_of` or `now` for the persisted `data_as_of` column.
- On cooldown, `get_realtime_revenue_snapshot` raises `RealtimeRevenueUnavailable`; endpoints return HTTP 503 with Retry-After.
- Freshness seconds: not returned on failure (503 path), but persisted `data_as_of` can be updated to a failure time.
- Verified: payload defaults to `False` on failure, but no central lock exists.

Conclusion:
- Freshness is computed at request time, not fetch completion time.
- Failure path can mutate `data_as_of` even without a successful fetch.
- Verified is not centrally enforced; it is derived from payload.

## Step C — Inspect persisted cache schema

Commands:
- Get-Content alembic/versions/007_skeldir_foundation/202601281230_b060_phase3_realtime_revenue_cache.py
- Get-Content backend/app/models/revenue_cache.py

Findings:
- `revenue_cache_entries` schema includes: `tenant_id`, `cache_key`, `payload` (jsonb), `data_as_of` (timestamptz), `expires_at`, `error_cooldown_until`, `last_error_at`, `last_error_message`, `etag`.
- RLS enforced via `tenant_isolation_policy` using `app.current_tenant_id`.

Conclusion:
- Fetch-time can be persisted in `data_as_of`, but semantics around updates need tightening to avoid mutation on failure or request-time.

## Step D — Confirm CI adjudication surface

Commands:
- Get-Content scripts/phase_gates/b0_6_gate.py
- Get-Content docs/phases/phase_manifest.yaml
- Get-Content .github/workflows/ci.yml

Findings:
- B0.6 phase gate is defined in `scripts/phase_gates/b0_6_gate.py` and invoked by CI via `python scripts/phase_gates/run_phase.py B0.6` (see `docs/phases/phase_manifest.yaml` + `.github/workflows/ci.yml` phase-gates job).
- Current gate runs only `backend/tests/test_b060_phase3_realtime_revenue_cache.py` after migrations.

Conclusion:
- Phase 5 tests must be added to `scripts/phase_gates/b0_6_gate.py` (or phase manifest) to ensure merge-blocking execution under CI phase gate.

## Hypothesis status (H5)

- H5-1 (Freshness computed at request-time): CONFIRMED. `backend/app/api/attribution.py` uses `datetime.now(...)` to compute `data_freshness_seconds`.
- H5-2 (Cache hit overwrites fetch-time): PARTIALLY CONFIRMED. Cache hit uses stored payload `data_as_of`, but `RealtimeRevenueSnapshot.from_payload` falls back to `_utcnow()` when missing, and failure path can overwrite `data_as_of`.
- H5-3 (Follower path lies about fetch-time): CONFIRMED for freshness. Follower uses leader payload for `data_as_of`, but freshness is computed at follower request time.
- H5-4 (verified derived/not locked): CONFIRMED. No canonical response lock; verified comes from snapshot payload.
- H5-5 (Failure/cooldown mutates fetch-time): CONFIRMED. `_record_failure` writes `data_as_of=now` when existing data is absent (and can update data_as_of column).
- H5-6 (Tests not adjudicated in CI): CONFIRMED. B0.6 gate does not include Phase 5 tests.

## Root-cause hypotheses (RH5) alignment

- RH5-A (Semantics not encoded as invariant tests): SUPPORTED. No Phase 5 tests exist; CI gate runs Phase 3 tests only.
- RH5-B (Time not injectable): SUPPORTED. Freshness uses direct `datetime.now()` in endpoint; cache uses `_utcnow()` with no injected clock.
- RH5-C (Response assembly duplicated): CONFIRMED. Two endpoints build responses directly.

## Stop condition check

- Canonical response builders identified: `backend/app/api/attribution.py` and `backend/app/api/revenue.py`.
- Cache service identified: `backend/app/services/realtime_revenue_cache.py`.
- Provider aggregator identified: `backend/app/services/realtime_revenue_providers.py`.
- CI gate identified: `scripts/phase_gates/b0_6_gate.py` invoked by phase-gates job in `.github/workflows/ci.yml`.

Stop condition satisfied: Phase 5 remediation can proceed after this note.
