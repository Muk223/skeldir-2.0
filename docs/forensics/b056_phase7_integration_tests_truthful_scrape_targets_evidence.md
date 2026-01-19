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

This environment does not include a local Postgres service (`psql` not present), so the full 3-process topology could not be executed here.

What was executed locally as correctness/compile gates:

### 4.1 Python bytecode compile

```powershell
python -m compileall backend\\app backend\\tests -q
```

### 4.2 Phase 5 topology unit/integration-ish tests (exporter subprocess)

```powershell
cd backend
python -m pytest tests/test_b0565_task_metrics_topology.py -q
```

Observed result (truncated):

- `7 passed, 1 skipped`

### 4.3 Phase 3 metrics hardening tests (API `/metrics` filtering)

```powershell
cd backend
python -m pytest tests/test_b0563_metrics_hardening.py -q
```

Observed result (truncated):

- `17 passed`

### 4.4 Legacy foundation test updated for split-brain (single test)

```powershell
cd backend
python -m pytest tests/test_b051_celery_foundation.py -k "api_metrics_exposed" -q
```

Observed result:

- `1 passed, 5 deselected`

## 5) CI run link and provenance

- Commit SHA: `0d6aac0`
- CI run URL: https://github.com/Muk223/skeldir-2.0/actions/runs/21149266087

Once merged, this section must be updated with the adjudicated commit SHA and the GitHub Actions run URL showing `tests/test_b0567_integration_truthful_scrape_targets.py` passing.
