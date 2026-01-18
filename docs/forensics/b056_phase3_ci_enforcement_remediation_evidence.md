# B0.5.6 Phase 3: CI Enforcement Remediation Evidence

**Date**: 2026-01-18  
**Phase**: B0.5.6.3 Metrics Hardening: Cardinality/Privacy Enforcement as Tests  
**Status**: COMPLETE  
**Acceptance Commit**: 3afd141  
**Acceptance CI Run**: https://github.com/Muk223/skeldir-2.0/actions/runs/21116761325

---

## 0. Objective

Primary adjudication failure mode: Phase 3 hardening tests existed, but were not executed in CI, therefore they were not an enforcement boundary.

This evidence pack validates/refutes the blocking hypotheses and proves CI execution of:
`backend/tests/test_b0563_metrics_hardening.py`.

---

## 1. Hypotheses (Unvalidated) → Results

### H-BLOCK-1 — Phase 3 tests are not executed in CI

**Validated (true)** for the referenced ledger run `21104399289`: CI used a pinned pytest allowlist that ended at `tests/test_b0562_health_semantics.py` and did not include Phase 3.

### H-BLOCK-2 — Ledger row points to a CI run that did not validate Phase 3 gates

**Validated (true)**: the Phase 3 ledger entry referenced CI run `21104399289`, which did not execute Phase 3 tests.

### H-BLOCK-3 — CI cannot run Phase 3 tests due to runtime dependencies (needs live API)

**Refuted (false)**: Phase 3 tests scrape `/metrics` in-process via `httpx.ASGITransport(app=app)` (no live server required). CI runs them inside the same pytest job.

---

## 2. Mandatory Empirical Validation

### V1 — Prove how CI selects tests (authoritative)

**Command (authoritative selection mechanism):**
```
type .github\workflows\ci.yml | findstr /n /i "pytest"
```

**Output (after remediation):**
```
385:            pytest tests/test_llm_payload_contract.py -q
389:          pytest tests/test_b052_queue_topology_and_dlq.py -q -k "QueueTopology"
598:          pytest \
608:            tests/test_b0563_metrics_hardening.py -q | tee "$B055_EVIDENCE_DIR/LOGS/pytest_b055.log"
884:      - name: Gate 2A - DSN Fingerprint Diagnostic (Pre-Pytest)
890:          echo "=== Gate 2A: DSN Fingerprint Diagnostic (Pre-Pytest Env State) ==="
995:          pytest tests/test_b0533_revenue_input_contract.py -v --tb=short
997:          echo "??? R5-5 MET / G5 PASSED: Contract tests executed (see pytest output above for pass/fail status)"
```

**Command (explicit Phase 3 presence):**
```
type .github\workflows\ci.yml | findstr /n /i "b0563 metrics_hardening test_b0563"
```

**Output (after remediation):**
```
608:            tests/test_b0563_metrics_hardening.py -q | tee "$B055_EVIDENCE_DIR/LOGS/pytest_b055.log"
```

**Command (file exists under backend tests):**
```
dir backend\tests | findstr /i "b0563"
```

**Output:**
```
-a----         1/18/2026  12:44 PM          15109 test_b0563_metrics_hardening.py
```

**Pre-remediation pytest allowlist (commit a45ee84):**
```
 598:           pytest \
 599:             tests/test_b051_celery_foundation.py \
 600:             tests/test_b052_queue_topology_and_dlq.py \
 601:             tests/test_b0532_window_idempotency.py \
 602:             tests/test_b055_llm_worker_stubs.py \
 603:             tests/test_b055_llm_model_parity.py \
 604:             tests/test_b055_llm_payload_fidelity.py \
 605:             tests/test_b055_matview_boundary.py \
 606:             tests/test_b055_tenant_propagation.py \
 607:             tests/test_b0562_health_semantics.py -q | tee "$B055_EVIDENCE_DIR/LOGS/pytest_b055.log"
```

**Post-remediation pytest allowlist (commit 3afd141):**
```
 598:           pytest \
 599:             tests/test_b051_celery_foundation.py \
 600:             tests/test_b052_queue_topology_and_dlq.py \
 601:             tests/test_b0532_window_idempotency.py \
 602:             tests/test_b055_llm_worker_stubs.py \
 603:             tests/test_b055_llm_model_parity.py \
 604:             tests/test_b055_llm_payload_fidelity.py \
 605:             tests/test_b055_matview_boundary.py \
 606:             tests/test_b055_tenant_propagation.py \
 607:             tests/test_b0562_health_semantics.py \
 608:             tests/test_b0563_metrics_hardening.py -q | tee "$B055_EVIDENCE_DIR/LOGS/pytest_b055.log"
```

---

### V2 — Prove Phase 3 tests are collected/executed (simulate CI command)

**Command (pre-remediation equivalent collection: no Phase 3 file in invocation):**
```
cd backend
pytest tests/test_b051_celery_foundation.py tests/test_b052_queue_topology_and_dlq.py tests/test_b0532_window_idempotency.py tests/test_b055_llm_worker_stubs.py tests/test_b055_llm_model_parity.py tests/test_b055_llm_payload_fidelity.py tests/test_b055_matview_boundary.py tests/test_b055_tenant_propagation.py tests/test_b0562_health_semantics.py --collect-only -q | Select-String -Pattern "test_b0563_metrics_hardening" -Context 0,1
```

**Output (pre-remediation equivalent):**
```
```

**Command (post-remediation collection includes Phase 3):**
```
cd backend
pytest tests/test_b051_celery_foundation.py tests/test_b052_queue_topology_and_dlq.py tests/test_b0532_window_idempotency.py tests/test_b055_llm_worker_stubs.py tests/test_b055_llm_model_parity.py tests/test_b055_llm_payload_fidelity.py tests/test_b055_matview_boundary.py tests/test_b055_tenant_propagation.py tests/test_b0562_health_semantics.py tests/test_b0563_metrics_hardening.py --collect-only -q | Select-String -Pattern "backend/tests/test_b0563_metrics_hardening\.py"
```

**Output (post-remediation collection):**
```
backend/tests/test_b0563_metrics_hardening.py::test_eg31_no_tenant_id_in_metric_definitions
backend/tests/test_b0563_metrics_hardening.py::test_eg31_no_tenant_id_in_metrics
backend/tests/test_b0563_metrics_hardening.py::test_eg34_no_uuid_values_in_metrics
backend/tests/test_b0563_metrics_hardening.py::test_eg32_metric_label_keys_are_allowlisted
backend/tests/test_b0563_metrics_hardening.py::test_eg32_closed_set_label_keys
backend/tests/test_b0563_metrics_hardening.py::test_eg32_task_name_values_bounded
backend/tests/test_b0563_metrics_hardening.py::test_eg32_queue_values_bounded
backend/tests/test_b0563_metrics_hardening.py::test_eg32_outcome_values_bounded
backend/tests/test_b0563_metrics_hardening.py::test_eg32_view_name_values_bounded
backend/tests/test_b0563_metrics_hardening.py::test_eg33_series_budget_computed
backend/tests/test_b0563_metrics_hardening.py::test_eg33_series_budget_within_threshold
backend/tests/test_b0563_metrics_hardening.py::test_eg33_all_dimensions_are_closed_sets
backend/tests/test_b0563_metrics_hardening.py::test_metrics_endpoint_returns_200
backend/tests/test_b0563_metrics_hardening.py::test_metrics_contains_expected_families
backend/tests/test_b0563_metrics_hardening.py::test_multiprocess_mode_detection
backend/tests/test_b0563_metrics_hardening.py::test_multiprocess_mode_env_documented
```

---

### V3 — Determine runtime dependencies of Phase 3 tests

**Source**: `backend/tests/test_b0563_metrics_hardening.py`

**Evidence (in-process scrape, no live API required):**
```
from httpx import AsyncClient, ASGITransport
from app.main import app

transport = ASGITransport(app=app)
async with AsyncClient(transport=transport, base_url="http://test") as client:
    resp = await client.get("/metrics")
```

---

### V4 — Prove ledger correctness was invalid

**Command (pre-remediation ledger row):**
```
type docs\forensics\INDEX.md | findstr /i /c:"| B0.5.6 Phase 3 |"
```

**Output (pre-remediation ledger row):**
```
| B0.5.6 Phase 3 | docs/forensics/b056_phase3_metrics_hardening_remediation_evidence.md | Metrics hardening: cardinality/privacy enforcement as tests | 7fda633 | https://github.com/Muk223/skeldir-2.0/actions/runs/21104399289 |
```

**Evidence: referenced CI run did not execute Phase 3 tests (run 21104399289):**
```
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:15.2489548Z [36;1m  tests/test_b0562_health_semantics.py -q | tee 
"$B055_EVIDENCE_DIR/LOGS/pytest_b055.log"[0m
  Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:15.2523246Z shell: /usr/bin/bash -e {0}
  Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:15.2523476Z env:
  Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:15.2523715Z   ADJUDICATED_SHA: 
7fda633c21ce85e7e9f5353a5d573781b0015bd0
  Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:15.2524284Z   DATABASE_URL: 
***127.0.0.1:5432/skeldir_validation
  Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:15.2524779Z   CELERY_BROKER_URL: 
***127.0.0.1:5432/skeldir_validation
  Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:15.2525333Z   CELERY_RESULT_BACKEND: 
***127.0.0.1:5432/skeldir_validation
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:24.4411336Z 
tests/test_b0562_health_semantics.py::test_eg1_openapi_route_uniqueness PASSED [ 78%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:24.4441222Z 
tests/test_b0562_health_semantics.py::test_eg2_liveness_returns_200_ok PASSED [ 80%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:24.4482268Z 
tests/test_b0562_health_semantics.py::test_eg2_liveness_no_db_calls PASSED [ 81%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:24.4522733Z 
tests/test_b0562_health_semantics.py::test_eg2_liveness_no_celery_calls PASSED [ 83%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:24.4862999Z 
tests/test_b0562_health_semantics.py::test_eg3_readiness_success PASSED  [ 85%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:24.4892915Z 
tests/test_b0562_health_semantics.py::test_eg3_readiness_failure_on_db_error PASSED [ 86%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:25.0263333Z 
tests/test_b0562_health_semantics.py::test_eg4_worker_capability_payload_structure PASSED [ 88%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:25.0302648Z 
tests/test_b0562_health_semantics.py::test_eg4_worker_success_with_mock PASSED [ 90%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:25.0336408Z 
tests/test_b0562_health_semantics.py::test_eg4_worker_failure_on_timeout PASSED [ 91%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:25.0365331Z 
tests/test_b0562_health_semantics.py::test_eg4_worker_failure_on_broker_error PASSED [ 93%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:25.0414082Z 
tests/test_b0562_health_semantics.py::test_eg5_probe_caching PASSED      [ 95%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:25.1968228Z 
tests/test_b0562_health_semantics.py::test_eg5_cache_expiry PASSED       [ 96%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:25.1993123Z 
tests/test_b0562_health_semantics.py::test_health_alias_returns_ok PASSED [ 98%]
> Celery Foundation B0.5.1	UNKNOWN STEP	2026-01-18T02:12:28.3296478Z 
tests/test_b0562_health_semantics.py::test_metrics_endpoint_still_works PASSED [100%]
```

**Evidence: acceptance CI run executes Phase 3 tests (run 21116761325):**
```
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:02.6432144Z [36;1m  
tests/test_b0563_metrics_hardening.py -q | tee "$B055_EVIDENCE_DIR/LOGS/pytest_b055.log"[0m
  Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:02.6463813Z shell: /usr/bin/bash -e {0}
  Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:02.6464041Z env:
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9431728Z 
tests/test_b0563_metrics_hardening.py::test_eg31_no_tenant_id_in_metric_definitions PASSED [ 80%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9475692Z 
tests/test_b0563_metrics_hardening.py::test_eg31_no_tenant_id_in_metrics PASSED [ 81%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9512400Z 
tests/test_b0563_metrics_hardening.py::test_eg34_no_uuid_values_in_metrics PASSED [ 82%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9521115Z 
tests/test_b0563_metrics_hardening.py::test_eg32_metric_label_keys_are_allowlisted PASSED [ 84%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9558258Z 
tests/test_b0563_metrics_hardening.py::test_eg32_closed_set_label_keys PASSED [ 85%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9596450Z 
tests/test_b0563_metrics_hardening.py::test_eg32_task_name_values_bounded PASSED [ 86%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9632357Z 
tests/test_b0563_metrics_hardening.py::test_eg32_queue_values_bounded PASSED [ 88%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9668878Z 
tests/test_b0563_metrics_hardening.py::test_eg32_outcome_values_bounded PASSED [ 89%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9704800Z 
tests/test_b0563_metrics_hardening.py::test_eg32_view_name_values_bounded PASSED [ 90%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9713476Z 
tests/test_b0563_metrics_hardening.py::test_eg33_series_budget_computed PASSED [ 92%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9722118Z 
tests/test_b0563_metrics_hardening.py::test_eg33_series_budget_within_threshold PASSED [ 93%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9730139Z 
tests/test_b0563_metrics_hardening.py::test_eg33_all_dimensions_are_closed_sets PASSED [ 94%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9764430Z 
tests/test_b0563_metrics_hardening.py::test_metrics_endpoint_returns_200 PASSED [ 96%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9798959Z 
tests/test_b0563_metrics_hardening.py::test_metrics_contains_expected_families PASSED [ 97%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:12.9817753Z 
tests/test_b0563_metrics_hardening.py::test_multiprocess_mode_detection PASSED [ 98%]
> Celery Foundation B0.5.1	Run Celery foundation tests	2026-01-18T18:46:17.0830316Z 
tests/test_b0563_metrics_hardening.py::test_multiprocess_mode_env_documented PASSED [100%]
```

---

## 3. Remediation

### R1 — Make Phase 3 tests unskippable in CI

Implemented: `.github/workflows/ci.yml` pytest allowlist now includes:
`tests/test_b0563_metrics_hardening.py`.

### R2 — Runtime orchestration (if needed)

Not required: tests are in-process and do not require a live server.

### R3 — Ledger update

Updated `docs/forensics/INDEX.md` to point Phase 3 to:
- commit `3afd141`
- CI run `https://github.com/Muk223/skeldir-2.0/actions/runs/21116761325`

---

## 4. Exit Gates (Binary)

| Gate | Status | Proof |
|------|--------|-------|
| EG3-A CI selection | PASS | `ci.yml` contains `tests/test_b0563_metrics_hardening.py` |
| EG3-B Runtime orchestration | PASS | Tests run in CI, not skipped |
| EG3-C Enforcement | PASS | Assertions include tenant_id, UUID, allowlisted labels, series budget; CI runs them |
| EG3-D Acceptance CI | PASS | https://github.com/Muk223/skeldir-2.0/actions/runs/21116761325 |
| EG3-E Ledger closure | PASS | `docs/forensics/INDEX.md` updated to acceptance commit + run |
