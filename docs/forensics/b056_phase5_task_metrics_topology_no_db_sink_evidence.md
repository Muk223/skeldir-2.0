# B0.5.6 Phase 5: Task Metrics Topology (No DB Sink) — Evidence Pack

**Date**: 2026-01-18  
**Scope**: B0.5.6.5 “Task Metrics Topology: Keep Metrics In-Memory, Scrape Workers Safely (No DB Sink)”  
**Status**: IMPLEMENTED (local verification); CI/acceptance pending

---

## 1) Objective / Invariants

This phase enforces a worker task-metrics topology where:

- Workers emit task metrics via `prometheus_client` multiprocess shards (in-memory → PID-sharded files).
- Exporter is the only HTTP listener for worker task metrics and is **read-only** w.r.t. `PROMETHEUS_MULTIPROC_DIR`.
- No telemetry is persisted to Postgres (no DB sink in the metrics path).
- Stale shard “zombies” are bounded and actively pruned by the worker parent (not exporter).
- Config is convergent (single env parsing + fail-fast validation).
- Cardinality/privacy is enforced (no `tenant_id`, no UUID-like label values).

---

## 2) Baseline (against `HEAD` before remediation)

### 2.1 Worker HTTP listener drift check (repo-wide scan)

**Command**
```powershell
git grep -n -E "wsgiref|http\.server|socketserver|start_http_server\(|make_server\(|serve_forever\(" HEAD -- backend/app
```

**Output**
```
(no matches)
```

### 2.2 Existing metrics exposure surfaces (pattern scan)

**Command**
```powershell
git grep -n -E "start_http_server|wsgiref|simple_server|serve_forever|/metrics|exporter" HEAD -- backend/app
```

**Output**
```
HEAD:backend/app/api/health.py:354:@router.get("/metrics")
HEAD:backend/app/celery_app.py:231:    B0.5.6.1: Worker-side HTTP server removed. Metrics are exposed exclusively via API /metrics.
HEAD:backend/app/config/contract_scope.yaml:17:  - /metrics
HEAD:backend/app/core/config.py:61:    # Worker-side HTTP server eradicated; metrics exposed via API /metrics only.
HEAD:backend/app/observability/broker_queue_stats.py:10:- Safe: TTL cache + single-flight refresh to avoid DB DoS via /metrics scrapes
HEAD:backend/app/observability/broker_queue_stats.py:84:# Cache always exists (even if zeroed) so /metrics never crashes.
HEAD:backend/app/observability/metrics.py:16:    and the /metrics endpoint aggregates them via MultiProcessCollector.
HEAD:backend/app/observability/metrics.py:24:    worker handling the /metrics scrape will report its own values.
HEAD:backend/app/tasks/context.py:109:    guarantees a correlation_id is present for downstream logs/metrics.
HEAD:backend/app/tasks/housekeeping.py:7:- Logging/metrics instrumentation
HEAD:backend/app/tasks/housekeeping.py:105:        fail: when True, force a failure to exercise error paths/metrics.
HEAD:backend/app/tasks/matviews.py:4:Delegates to the matview executor and emits logs/metrics/DLQ-triggering
```

### 2.3 `celery_task_*` metric production points

**Command**
```powershell
git grep -n "celery_task_" HEAD -- backend/app
```

**Output**
```
HEAD:backend/app/celery_app.py:360:    metrics.celery_task_started_total.labels(task_name=normalized_name).inc()
HEAD:backend/app/celery_app.py:370:        metrics.celery_task_duration_seconds.labels(task_name=normalized_name).observe(duration)
HEAD:backend/app/celery_app.py:372:        metrics.celery_task_success_total.labels(task_name=normalized_name).inc()
HEAD:backend/app/celery_app.py:383:    metrics.celery_task_failure_total.labels(task_name=normalized_name).inc()
HEAD:backend/app/celery_app.py:385:        "celery_task_failed",
HEAD:backend/app/core/config.py:186:    def validate_celery_task_time_limits(cls, value: int, info) -> int:
HEAD:backend/app/observability/metrics.py:63:celery_task_started_total = Counter(
HEAD:backend/app/observability/metrics.py:64:    "celery_task_started_total",
HEAD:backend/app/observability/metrics.py:69:celery_task_success_total = Counter(
HEAD:backend/app/observability/metrics.py:70:    "celery_task_success_total",
HEAD:backend/app/observability/metrics.py:75:celery_task_failure_total = Counter(
HEAD:backend/app/observability/metrics.py:76:    "celery_task_failure_total",
HEAD:backend/app/observability/metrics.py:81:celery_task_duration_seconds = Histogram(
HEAD:backend/app/observability/metrics.py:82:    "celery_task_duration_seconds",
HEAD:backend/app/observability/metrics_policy.py:212:    # - celery_task_* metrics: task_name only
HEAD:backend/app/observability/metrics_policy.py:217:    celery_task_series = dim_task_names  # task_name only
HEAD:backend/app/observability/metrics_policy.py:229:    celery_total = 4 * celery_task_series
HEAD:backend/app/tasks/housekeeping.py:112:            "celery_task_start",
HEAD:backend/app/tasks/housekeeping.py:140:            "celery_task_success",
```

### 2.4 `PROMETHEUS_MULTIPROC_DIR` reads

**Command**
```powershell
git grep -n "PROMETHEUS_MULTIPROC_DIR" HEAD -- backend/app
```

**Output**
```
HEAD:backend/app/api/health.py:330:    When PROMETHEUS_MULTIPROC_DIR is set, uses MultiProcessCollector to
HEAD:backend/app/api/health.py:335:    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
HEAD:backend/app/api/health.py:359:    B0.5.6.3: Supports multiprocess mode when PROMETHEUS_MULTIPROC_DIR is set.
HEAD:backend/app/api/health.py:365:        PROMETHEUS_MULTIPROC_DIR: Directory for multiprocess metric files.
HEAD:backend/app/observability/metrics.py:14:    PROMETHEUS_MULTIPROC_DIR to a writable directory BEFORE any prometheus_client
HEAD:backend/app/observability/metrics.py:19:        export PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
HEAD:backend/app/observability/metrics.py:20:        mkdir -p $PROMETHEUS_MULTIPROC_DIR
HEAD:backend/app/observability/metrics.py:23:    Without PROMETHEUS_MULTIPROC_DIR, metrics are process-local and only the
```

### 2.5 Exporter bind/port config (baseline)

**Command**
```powershell
git grep -n "WORKER_METRICS_EXPORTER_" HEAD -- backend/app
```

**Output**
```
(no matches)
```

### 2.6 Existing Celery signal hooks

**Command**
```powershell
git grep -n "@signals\." HEAD -- backend/app
```

**Output**
```
HEAD:backend/app/celery_app.py:226:@signals.worker_process_init.connect
HEAD:backend/app/celery_app.py:348:@signals.worker_ready.connect
HEAD:backend/app/celery_app.py:355:@signals.task_prerun.connect
HEAD:backend/app/celery_app.py:363:@signals.task_postrun.connect
HEAD:backend/app/celery_app.py:375:@signals.task_failure.connect
```

---

## 3) Remediation (current working tree)

### 3.1 Single-source metrics runtime config (R1)

- **File**: `backend/app/observability/metrics_runtime_config.py`
- **Contract**:
  - `PROMETHEUS_MULTIPROC_DIR` required, absolute, must exist and be writable/executable
  - fail-fast with canonical error string `MULTIPROC_DIR_INVALID_ERROR`
  - exporter bind: `WORKER_METRICS_EXPORTER_HOST` / `WORKER_METRICS_EXPORTER_PORT` (default `127.0.0.1:9108`)

### 3.2 Worker parent validation + lifecycle hooks (R2)

- **File**: `backend/app/celery_app.py`
  - `@signals.worker_init.connect` validates multiproc dir and enforces an overflow cap
  - `@signals.worker_process_shutdown.connect` calls `prometheus_client.multiprocess.mark_process_dead(pid)`
  - task metrics are still produced, but metrics imports are now lazy in the signal handlers

### 3.3 Parent-owned periodic pruning (R3)

- **Files**:
  - `backend/app/observability/multiprocess_shard_pruner.py` (conservative `*.db` pruning)
  - `backend/app/celery_app.py` (parent thread `prom-multiproc-sweeper`)
  - `backend/app/observability/metrics.py` (operational counters)

Operational counters (no labels):
- `multiproc_orphan_files_detected`
- `multiproc_pruned_files_total`
- `multiproc_dir_overflow_total`

### 3.4 Read-only exporter (R4)

- **File**: `backend/app/observability/worker_metrics_exporter.py`
- **Invariants**:
  - serves `/metrics` only
  - does not import settings/DB/Celery
  - does not delete/rename/modify files in the multiprocess directory

Read-only verification (no filesystem deletion calls present):
```powershell
git grep -n -E "unlink\(|rmtree\(|os\.remove\(|shutil\.rmtree\(|delete\(" -- backend/app/observability/worker_metrics_exporter.py
```
Output:
```
(no matches)
```

---

## 4) Provisioning Authority (Docker Compose)

**Chosen authority**: **Docker Compose** (named volume shared between worker and exporter).

**Contract**:
- `PROMETHEUS_MULTIPROC_DIR` is mounted at a fixed absolute path (e.g., `/prometheus-multiproc`).
- Both worker and exporter containers run with compatible UID/GID mappings so the directory is writable.
- Application code does not `mkdir` or change permissions; it **fails fast** if the directory is missing/unwritable.

---

## 5) Verification (local)

### 5.1 Guardrail: no worker HTTP server primitives

**Command**
```powershell
python scripts/ci/enforce_no_worker_http_server.py
```

**Output**
```
B0.5.6.1 Worker HTTP Server Guardrail Scan
Scanned: C:\Users\ayewhy\II SKELDIR II\backend\app
Violations: 0

PASS: No worker HTTP server primitives detected.
```

### 5.2 Phase 5 tests (pytest)

**Command**
```powershell
cd backend
$env:DATABASE_URL="postgresql+asyncpg://app_user:app_user@127.0.0.1:5432/skeldir_validation"
pytest -q tests/test_b0565_task_metrics_topology.py
```

**Output**
```
tests\test_b0565_task_metrics_topology.py::test_eg53_exporter_serves_metrics_with_invalid_database_url PASSED [ 12%]
tests\test_b0565_task_metrics_topology.py::test_eg52_worker_entrypoints_do_not_import_http_server_primitives PASSED [ 25%]
tests\test_b0565_task_metrics_topology.py::test_eg57_convergence_fail_fast_when_multiproc_dir_missing PASSED [ 37%]
tests\test_b0565_task_metrics_topology.py::test_eg57_convergence_fail_fast_when_multiproc_dir_not_absolute PASSED [ 50%]
tests\test_b0565_task_metrics_topology.py::test_eg57_convergence_fail_fast_when_multiproc_dir_unwritable SKIPPED [ 62%]
tests\test_b0565_task_metrics_topology.py::test_eg56_active_pruning_prunes_dead_pid_shards_but_keeps_live PASSED [ 75%]
tests\test_b0565_task_metrics_topology.py::test_eg55_worker_shutdown_hook_calls_mark_process_dead PASSED [ 87%]
tests\test_b0565_task_metrics_topology.py::test_eg58_task_metrics_labels_are_privacy_safe_and_bounded PASSED [100%]

======================== 7 passed, 1 skipped in 0.98s =========================
```

---

## 6) CI + Ledger Closure (pending)

This evidence pack requires a GitHub Actions run link and authoritative commit SHA after pushing.

- **Commit SHA**: pending (uncommitted working tree)
- **CI Run Link**: pending
- **INDEX row**: updated locally; update PR/commit + CI link upon push/merge

### 6.1 INDEX diff (local)

```diff
diff --git a/docs/forensics/INDEX.md b/docs/forensics/INDEX.md
index fde9399..da34ed0 100644
--- a/docs/forensics/INDEX.md
+++ b/docs/forensics/INDEX.md
@@ -28,6 +28,7 @@ This index enumerates evidence packs stored under `docs/forensics/`.
 | B0.5.6 Phase 3 | docs/forensics/b056_phase3_metrics_hardening_remediation_evidence.md | Metrics hardening: cardinality/privacy enforcement as tests | 3afd141 | https://github.com/Muk223/skeldir-2.0/actions/runs/21116761325 |
 | B0.5.6 Phase 3 CI enforcement | docs/forensics/b056_phase3_ci_enforcement_remediation_evidence.md | Proof that Phase 3 gates execute in CI (selection + logs) | 3afd141 | https://github.com/Muk223/skeldir-2.0/actions/runs/21116761325 |
 | B0.5.6 Phase 4 | docs/forensics/b056_phase4_queue_depth_max_age_broker_truth_evidence.md | Queue depth + max age gauges from broker truth (cached) | 1533ef2 | https://github.com/Muk223/skeldir-2.0/actions/runs/21117888714 |
+| B0.5.6 Phase 5 | docs/forensics/b056_phase5_task_metrics_topology_no_db_sink_evidence.md | Task metrics topology: exporter-only scrape, no DB sink, parent-owned pruning | pending | pending |
 
 ## Root evidence packs
 | Phase/Topic | Evidence pack | Purpose | PR/Commit | CI Run |
```
