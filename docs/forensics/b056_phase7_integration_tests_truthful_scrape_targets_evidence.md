# B0.5.6.7 — Integration Tests: Truthful Scrape Targets + No Split-Brain

This evidence pack locks the runtime topology truth into CI-enforced integration tests:

- Worker emits task metrics via Prometheus multiprocess shards in `PROMETHEUS_MULTIPROC_DIR` (no worker HTTP listener).
- Exporter is the only HTTP scrape surface for worker task metrics (`/metrics`).
- API `/metrics` exposes API metrics + broker-truth queue gauges only; it must not expose worker task metric families.

## 1) Investigation (source-of-truth mapping)

### I-A: Authoritative scrape targets and ports

- Exporter bind authority: `backend/app/observability/metrics_runtime_config.py:74`
  - `WORKER_METRICS_EXPORTER_HOST` default `127.0.0.1`: `backend/app/observability/metrics_runtime_config.py:75`
  - `WORKER_METRICS_EXPORTER_PORT` default `9108`: `backend/app/observability/metrics_runtime_config.py:76`
- Exporter scrape surface is `/metrics` only: `backend/app/observability/worker_metrics_exporter.py:33`
- Exporter HTTP server binds per config: `backend/app/observability/worker_metrics_exporter.py:49`
  - uses `make_server(...)`: `backend/app/observability/worker_metrics_exporter.py:51`
- API metrics route: `backend/app/api/health.py:360`
- Multiproc dir authority + fail-fast error: `backend/app/observability/metrics_runtime_config.py:18`
  - `get_multiproc_dir()` reads `PROMETHEUS_MULTIPROC_DIR`: `backend/app/observability/metrics_runtime_config.py:45`

### I-B: Existing tests touching `/metrics` (classified)

`rg -n "/metrics" backend/tests` (representative set):

- In-process (ASGITransport; unit/contract-ish):
  - `backend/tests/test_b047_logging_and_metrics_contract.py`
  - `backend/tests/test_b047_observability.py`
  - `backend/tests/test_b051_celery_foundation.py`
  - `backend/tests/test_b0562_health_semantics.py`
  - `backend/tests/test_b0563_metrics_hardening.py`
  - `backend/tests/test_b0564_queue_depth_max_age_broker_truth.py`
- Subprocess + HTTP (integration-ish):
  - `backend/tests/test_b0565_task_metrics_topology.py` (starts exporter subprocess; scrapes exporter `/metrics`)
  - `backend/tests/test_b0567_integration_truthful_scrape_targets.py` (starts API + worker + exporter; scrapes both `/metrics`)
- Subprocess (non-HTTP integration):
  - `backend/tests/test_b0566_structured_worker_logging_runtime.py` (starts worker subprocess; validates lifecycle JSON logs)

## 2) Remediation (implementation summary)

### R-1: CI-safe 3-process harness

- Harness: `backend/tests/metrics_topology_harness.py`
  - Starts:
    - API process (Uvicorn)
    - Worker process (Celery)
    - Exporter process (`app.observability.worker_metrics_exporter`)
  - Shares a single temp `PROMETHEUS_MULTIPROC_DIR` across all three, but the API strips it at startup to prevent split-brain.

### R-2: Truthful scrape-target integration tests

- Tests: `backend/tests/test_b0567_integration_truthful_scrape_targets.py`
  - T7.1: Worker task metrics delta appears on Exporter `/metrics`.
  - T7.2: API queue gauges match broker truth (computed by SQL query; compared to scraped gauges).
  - T7.3: Anti split-brain: API `/metrics` does not include worker task metric families.
  - T7.4: Privacy/cardinality: forbidden label keys (at least `tenant_id`) absent on both scrape surfaces.

## 3) Local run commands

### 3.1 Run the Phase 7 tests (requires Postgres + migrations + Celery deps)

From repo root:

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
python -m pytest tests/test_b0567_integration_truthful_scrape_targets.py -vv
```

### 3.2 Manual topology bring-up (reference)

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
$env:PROMETHEUS_MULTIPROC_DIR = "C:\\temp\\prom_multiproc"  # must exist and be writable
$env:WORKER_METRICS_EXPORTER_HOST = "127.0.0.1"
$env:WORKER_METRICS_EXPORTER_PORT = "9108"

# Worker (no metrics HTTP server)
python -m celery -A app.celery_app.celery_app worker -P solo -c 1 --loglevel=INFO

# Exporter (the only worker metrics scrape surface)
python -m app.observability.worker_metrics_exporter

# API (separate /metrics surface)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 4) Evidence captured in this environment

Local Windows environment constraints:

- No local Postgres service available (`psql` not present), so the full 3-process topology cannot be proven locally here.
- CI evidence below is therefore the acceptance authority for end-to-end topology proof.

## 5) Evaluation protocol evidence (EVAL-A/B/C)

### 5.1 EVAL-A — Acceptance SHA + contents (verbatim)

Acceptance SHA (Phase 7):

```text
git rev-parse 7fe6219f0ac4cba53179eec5b6e16d124e568304
7fe6219f0ac4cba53179eec5b6e16d124e568304

git show -s --oneline 7fe6219f0ac4cba53179eec5b6e16d124e568304
7fe6219 CI: add Backend Integration (B0567) job; rename Playwright job
```

Acceptance SHA (code + workflow) is pinned by INDEX Phase 7 row:

```text
| B0.5.6 Phase 7 | docs/forensics/b056_phase7_integration_tests_truthful_scrape_targets_evidence.md | Integration tests: truthful scrape targets (exporter vs API) + anti split-brain + privacy labels | 7fe6219 | https://github.com/Muk223/skeldir-2.0/actions/runs/21150928803 |
```

Pre-REM-1 provenance incoherence (validated): the Phase 7 test module existed at `0d6aac0`, but `docs/forensics/INDEX.md` still showed Phase 7 as `pending` at that SHA:

```text
git ls-tree -r 0d6aac0 --name-only | findstr b0567
backend/tests/test_b0567_integration_truthful_scrape_targets.py

git show 0d6aac0:docs/forensics/INDEX.md | findstr /c:"| B0.5.6 Phase 7 |"
| B0.5.6 Phase 7 | docs/forensics/b056_phase7_integration_tests_truthful_scrape_targets_evidence.md | Integration tests: truthful scrape targets (exporter vs API) + anti split-brain + privacy labels | pending | pending |

git show 0d6aac0:docs/forensics/b056_phase7_integration_tests_truthful_scrape_targets_evidence.md | findstr /c:"Commit SHA"
- Commit SHA: pending
```

### 5.2 EVAL-B — CI execution proof (log excerpts)

CI run (commit `c3707c8`) proving Phase 7 executed and passed:

- https://github.com/Muk223/skeldir-2.0/actions/runs/21149356100

Verbatim excerpt from job `Celery Foundation B0.5.1`:

```text
pytest \
  tests/test_b051_celery_foundation.py \
  ...
  tests/test_b0566_structured_worker_logging_runtime.py \
  tests/test_b0567_integration_truthful_scrape_targets.py \
  tests/test_b0564_queue_depth_max_age_broker_truth.py -q | tee "$B055_EVIDENCE_DIR/LOGS/pytest_b055.log"

tests/test_b0567_integration_truthful_scrape_targets.py::test_t71_task_metrics_delta_on_exporter PASSED [ 93%]
tests/test_b0567_integration_truthful_scrape_targets.py::test_t72_api_queue_gauges_match_broker_truth PASSED [ 94%]
tests/test_b0567_integration_truthful_scrape_targets.py::test_t73_api_metrics_do_not_include_worker_task_metrics PASSED [ 95%]
tests/test_b0567_integration_truthful_scrape_targets.py::test_t74_forbidden_labels_absent_on_both_scrape_surfaces PASSED [ 96%]
====================== 93 passed, 129 warnings in 29.89s =======================
```

### 5.3 EVAL-C — Topology semantics asserted by test code (pointers)

Phase 7 test module: `backend/tests/test_b0567_integration_truthful_scrape_targets.py`

- Exporter scrape for worker task deltas: `test_t71_task_metrics_delta_on_exporter`
- API scrape for broker-truth gauges: `test_t72_api_queue_gauges_match_broker_truth`
- Anti split-brain negative assertion: `test_t73_api_metrics_do_not_include_worker_task_metrics`
- Privacy label ban via scrape: `test_t74_forbidden_labels_absent_on_both_scrape_surfaces`

Broker-truth SQL (read-only) is implemented in `_fetch_broker_truth_normalized()` and compared to API gauges in `test_t72_api_queue_gauges_match_broker_truth`.

## 6) Remediation to eliminate “green illusion” ambiguity (REM-1)

`ci.yml` now contains an explicit backend job and disambiguated Playwright naming (acceptance commit `7fe6219`, CI run `21150928803`):

- Backend job: `Backend Integration (B0567)` (explicit `pytest -vv tests/test_b0567_integration_truthful_scrape_targets.py`)
- Playwright job renamed: `Frontend E2E (Playwright)`

Verbatim excerpt from `Backend Integration (B0567)` job log:

```text
pytest -vv tests/test_b0567_integration_truthful_scrape_targets.py
collecting ... collected 4 items
tests/test_b0567_integration_truthful_scrape_targets.py::test_t71_task_metrics_delta_on_exporter PASSED [ 25%]
tests/test_b0567_integration_truthful_scrape_targets.py::test_t72_api_queue_gauges_match_broker_truth PASSED [ 50%]
tests/test_b0567_integration_truthful_scrape_targets.py::test_t73_api_metrics_do_not_include_worker_task_metrics PASSED [ 75%]
tests/test_b0567_integration_truthful_scrape_targets.py::test_t74_forbidden_labels_absent_on_both_scrape_surfaces PASSED [100%]
============================== 4 passed in 11.18s ==============================
```

## 7) CI run link and provenance

- Phase 7 execution proof (pre-REM-1 disambiguation): commit `c3707c8`, run https://github.com/Muk223/skeldir-2.0/actions/runs/21149356100
- Phase 7 unskippable explicit job proof (REM-1): commit `7fe6219`, run https://github.com/Muk223/skeldir-2.0/actions/runs/21150928803
