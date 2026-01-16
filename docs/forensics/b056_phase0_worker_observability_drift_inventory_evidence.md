# B0.5.6 Phase 0: Worker Observability Drift Inventory Evidence

**Date**: 2026-01-15
**Investigator**: Claude (automated forensic audit)
**Scope**: Worker-side HTTP server observability surfaces, broker semantics, and Phase 5 hermetic compliance

---

## 1. Executive Findings (Evidence-Linked)

1. **Worker HTTP server IS active and binds sockets at runtime** - [worker_monitoring.py:85-113](backend/app/observability/worker_monitoring.py#L85-L113) starts a `wsgiref.simple_server` WSGI server in a daemon thread on `worker_process_init` signal
2. **Default bind address is `0.0.0.0:9540`** - [config.py:60-61](backend/app/core/config.py#L60-L61) exposes to all interfaces by default (network-accessible)
3. **Transitive socket usage bypasses hermeticity scanner** - `wsgiref.simple_server` → `http.server.HTTPServer` → `socketserver.TCPServer` → `import socket` (stdlib path not scanned)
4. **Multi-worker port conflicts are silent on Windows** - Two workers can both "bind" port 9540 via SO_REUSEADDR, creating non-deterministic scraping behavior
5. **`/metrics` endpoints exist on BOTH worker and API surfaces** - But registries are process-local and NOT unified; worker metrics don't appear in API metrics
6. **Worker `/health` performs broker+DB connectivity checks** - [worker_monitoring.py:24-49](backend/app/observability/worker_monitoring.py#L24-L49) validates both before returning healthy
7. **API `/health/ready` performs RLS policy validation** - [health.py:19-49](backend/app/api/health.py#L19-L49) checks DB connectivity AND RLS enforcement on `attribution_events`
8. **Broker is definitively Postgres via SQLAlchemy transport** - `sqla+postgresql://...` scheme with `kombu_message.visible` for reservation semantics
9. **`-P threads` pool does NOT start worker HTTP server** - `worker_process_init` signal doesn't fire for thread-based pools
10. **Metrics expose `tenant_id` labels** - [metrics.py:3-28](backend/app/observability/metrics.py#L3-L28) includes `tenant_id` in event counters (potential PII exposure)

---

## 2. Hypothesis Results

### H-DRIFT: Worker HTTP Server Activation
**VALIDATED** ✓

**Evidence:**
- **Import path**: [celery_app.py:23](backend/app/celery_app.py#L23) imports `start_worker_http_server`
- **Signal hook**: [celery_app.py:218-233](backend/app/celery_app.py#L218-L233) connects to `@signals.worker_process_init.connect`
- **Server start call**: [celery_app.py:225-229](backend/app/celery_app.py#L225-L229) calls `start_worker_http_server(celery_app, host=settings.CELERY_METRICS_ADDR, port=settings.CELERY_METRICS_PORT)`
- **Runtime proof**: Worker logs show `{"level": "INFO", "logger": "app.observability.worker_monitoring", "message": "celery_worker_metrics_server_started"}`
- **Port binding proof**: `netstat -an | findstr ":9540"` shows `TCP 0.0.0.0:9540 LISTENING`

**Concurrency behavior**:
- `-P solo` (single process): HTTP server starts, port binds successfully
- `-P threads` (threading pool): `worker_process_init` signal does NOT fire, HTTP server does NOT start
- Multiple `-P solo` workers: BOTH processes bind to same port (Windows SO_REUSEADDR behavior)

### H-METRICS: Unaudited /metrics Endpoints
**VALIDATED** ✓

**Worker-side `/metrics`** ([worker_monitoring.py:56-61](backend/app/observability/worker_monitoring.py#L56-L61)):
- Mount: `http://<CELERY_METRICS_ADDR>:<CELERY_METRICS_PORT>/metrics`
- Tech stack: `prometheus_client.make_wsgi_app()` over `wsgiref.simple_server.WSGIServer`
- Auth: None
- Sample output:
```
# HELP celery_task_started_total Total Celery tasks started
# TYPE celery_task_started_total counter
celery_task_started_total{task_name="app.tasks.matviews.refresh_all_for_tenant"} 60.0
celery_task_success_total{task_name="app.tasks.matviews.refresh_all_for_tenant"} 59.0
```

**API-side `/metrics`** ([health.py:52-55](backend/app/api/health.py#L52-L55)):
- Mount: `http://<API_HOST>:<API_PORT>/metrics` (via [main.py:52](backend/app/main.py#L52))
- Tech stack: `prometheus_client.generate_latest()` via FastAPI Response
- Auth: None
- Registry: Same default registry, but **process-local** (API and worker are separate processes)

**Critical issue**: Worker metrics (task counts, durations) do NOT appear in API `/metrics` because registries are process-isolated.

### H-HEALTH: Unaudited /health Endpoints
**VALIDATED** ✓

**Worker `/health`** ([worker_monitoring.py:63-77](backend/app/observability/worker_monitoring.py#L63-L77)):
- Checks: Broker connectivity (`_check_broker`) + Database connectivity (`_check_database`)
- Response: `{"status": "ok", "broker": "ok", "database": "ok"}` or `503 Service Unavailable`
- Semantics: Connectivity check only (SELECT 1 equivalent), NOT data-plane round-trip

**API `/health`** ([main.py:56-59](backend/app/main.py#L56-L59) and [health.py:14-16](backend/app/api/health.py#L14-L16)):
- Simple liveness: `{"status": "healthy"}` - NO connectivity checks
- Mounted twice (duplicate routes)

**API `/health/ready`** ([health.py:19-49](backend/app/api/health.py#L19-L49)):
- Checks: DB connectivity + RLS policy enforcement + tenant context GUC validation
- Response: `{"status":"ready","checks":{"database":"ok"}}` or `503`
- Semantics: More comprehensive than worker `/health`

### H-BROKER: Postgres SQLAlchemy Transport
**VALIDATED** ✓

**Broker URL**: `sqla+postgresql://app_user:***@localhost:5432/skeldir_validation`
- Built by [celery_app.py:76-86](backend/app/celery_app.py#L76-L86) from `DATABASE_URL`

**Table schema**:
```
kombu_queue:
  id: integer (PK)
  name: character varying

kombu_message:
  id: integer (PK)
  visible: boolean (reservation flag)
  timestamp: timestamp without time zone (enqueue time)
  payload: text (JSON task body)
  version: smallint
  queue_id: integer (FK)
```

**Queue depth SQL** (read-only):
```sql
SELECT
    q.name AS queue_name,
    SUM(CASE WHEN m.visible THEN 1 ELSE 0 END) AS visible_count,
    SUM(CASE WHEN NOT m.visible THEN 1 ELSE 0 END) AS invisible_count,
    COUNT(*) AS total
FROM kombu_queue q
LEFT JOIN kombu_message m ON m.queue_id = q.id
WHERE q.name NOT LIKE '%.reply.celery.pidbox'
GROUP BY q.name;
```

**Max age SQL** (read-only):
```sql
SELECT
    q.name AS queue_name,
    MIN(m.timestamp) AS oldest_message,
    EXTRACT(EPOCH FROM (NOW() - MIN(m.timestamp))) AS max_age_seconds
FROM kombu_queue q
LEFT JOIN kombu_message m ON m.queue_id = q.id
WHERE m.timestamp IS NOT NULL
  AND q.name NOT LIKE '%.reply.celery.pidbox'
GROUP BY q.name;
```

**Recovery logic**: [celery_app.py:236-327](backend/app/celery_app.py#L236-L327)
- `_recover_invisible_kombu_messages()` sets `visible=true` for messages older than `CELERY_BROKER_VISIBILITY_TIMEOUT_S` (default 3600s)
- Runs in daemon thread via `_start_kombu_visibility_recovery_thread()`
- Sweep interval: `CELERY_BROKER_RECOVERY_SWEEP_INTERVAL_S` (default 1.0s)

### H-HERMETIC-NUANCE: Transitive Socket Usage
**VALIDATED** ✓

**Import chain**:
```
worker_monitoring.py:14
  → from wsgiref.simple_server import make_server, WSGIServer
    → [C:\Python311\Lib\wsgiref\simple_server.py:13]
      → from http.server import BaseHTTPRequestHandler, HTTPServer
        → [C:\Python311\Lib\http\server.py] inherits socketserver.TCPServer
          → [C:\Python311\Lib\socketserver.py:126]
            → import socket
```

**Scanner behavior** ([scripts/ci/enforce_runtime_hermeticity.py](scripts/ci/enforce_runtime_hermeticity.py)):
- `FORBIDDEN_MODULES` includes `"socket"` (line 23)
- But scanner only parses **direct imports in app code**, not stdlib transitive imports
- `wsgiref` is stdlib, not in `FORBIDDEN_MODULES`
- Scanner passes because it doesn't see `import socket` directly in `worker_monitoring.py`

**Runtime socket proof**:
```
$ netstat -an | findstr ":9540"
TCP    0.0.0.0:9540    0.0.0.0:0    LISTENING
```

---

## 3. Static Path Map

### Entrypoint → Sidecar Startup Chain

```
Celery worker startup
    │
    ▼
celery_app.py (module load)
    │ line 23: from app.observability.worker_monitoring import start_worker_http_server
    │ line 630: _ensure_celery_configured()
    │
    ▼
@signals.worker_process_init.connect (line 218)
    │ _configure_worker_logging(**kwargs)
    │
    ▼
start_worker_http_server() called (line 225-229)
    │ host=settings.CELERY_METRICS_ADDR (default "0.0.0.0")
    │ port=settings.CELERY_METRICS_PORT (default 9540)
    │
    ▼
worker_monitoring.py:85 - start_worker_http_server()
    │ Global _server_started guard (line 91-95)
    │ Build WSGI app via _build_app() (line 97)
    │
    ▼
worker_monitoring.py:99-113 - _run() in daemon thread
    │ wsgiref.simple_server.make_server(host, port, app)
    │ httpd.serve_forever()
    │
    ▼
Port bound, endpoints active:
    /metrics → prometheus_client.make_wsgi_app()
    /health  → broker + DB connectivity checks
```

### Endpoint Inventory Table

| Endpoint | Location | Tech Stack | Auth | Intended Audience |
|----------|----------|------------|------|-------------------|
| Worker `/metrics` | `worker_monitoring.py:60-61` | wsgiref + prometheus_client WSGI | None | Internal/Prometheus |
| Worker `/health` | `worker_monitoring.py:63-77` | wsgiref + JSON response | None | Internal/k8s probes |
| API `/metrics` | `health.py:52-55` | FastAPI + prometheus_client | None | Internal/Prometheus |
| API `/health` | `main.py:56-59` | FastAPI | None | External/load balancer |
| API `/health` | `health.py:14-16` | FastAPI | None | Duplicate route |
| API `/health/ready` | `health.py:19-49` | FastAPI + DB/RLS checks | None | Internal/k8s readiness |

---

## 4. Runtime Audit Evidence

### 4.1 Single Worker Process Bind Proof

**Command**: `python -m celery -A app.celery_app.celery_app worker -P solo -c 1 --loglevel=INFO`

**Startup logs** (truncated):
```json
{"level": "INFO", "logger": "app.celery_app", "message": "celery_worker_logging_configured"}
{"level": "INFO", "logger": "app.observability.worker_monitoring", "message": "celery_worker_metrics_server_started"}
```

**Port binding**:
```
$ netstat -an | findstr ":9540"
TCP    0.0.0.0:9540    0.0.0.0:0    LISTENING
```

**Health endpoint response**:
```
$ curl -s http://127.0.0.1:9540/health
{"status": "ok", "broker": "ok", "database": "ok"}
```

**Metrics endpoint response** (sample):
```
# HELP celery_task_started_total Total Celery tasks started
# TYPE celery_task_started_total counter
celery_task_started_total{task_name="app.tasks.matviews.refresh_all_for_tenant"} 60.0
celery_task_started_total{task_name="app.tasks.matviews.pulse_matviews_global"} 1.0
# HELP celery_task_success_total Total Celery tasks succeeded
# TYPE celery_task_success_total counter
celery_task_success_total{task_name="app.tasks.matviews.refresh_all_for_tenant"} 59.0
```

### 4.2 Multi-Process Bind Conflict Test

**Test**: Two `-P solo` workers started simultaneously

**Result** (Windows-specific):
```
$ netstat -an | findstr ":9540"
TCP    0.0.0.0:9540    0.0.0.0:0    LISTENING
TCP    0.0.0.0:9540    0.0.0.0:0    LISTENING
```

**Observation**: Windows allows both processes to bind via SO_REUSEADDR. Both log `celery_worker_metrics_server_started` without error. Only one receives incoming connections (OS-level routing). This creates non-deterministic scraping behavior.

**Note**: On Linux with SO_REUSEADDR not set, second bind would fail with `OSError: [Errno 98] Address already in use`.

### 4.3 Thread Pool Behavior

**Command**: `python -m celery -A app.celery_app.celery_app worker -P threads -c 2 --loglevel=INFO`

**Result**: HTTP server does NOT start. `worker_process_init` signal does not fire for thread-based pools.

```
$ netstat -an | findstr ":9540"
(no output - port not bound)
```

### 4.4 API /metrics Check

**Command**: `uvicorn app.main:app --host 127.0.0.1 --port 8000`

**Endpoints tested**:
```
$ curl -s http://127.0.0.1:8000/health
{"status":"healthy"}

$ curl -s http://127.0.0.1:8000/health/ready
{"status":"ready","checks":{"database":"ok"}}

$ curl -s http://127.0.0.1:8000/metrics | head -5
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 791.0
```

**Critical observation**: API `/metrics` shows metric definitions but NO worker task counts because registries are process-isolated.

---

## 5. DB Forensics + Queries Used

### Broker Configuration

**Confirmed broker URL at runtime**:
```python
from app.celery_app import _build_broker_url
print(_build_broker_url())
# Output: sqla+postgresql://app_user:app_user@localhost:5432/skeldir_validation
```

### Kombu Table Schemas

```sql
-- kombu_queue schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'kombu_queue';

-- Result:
-- id: integer (NO)
-- name: character varying (NO)

-- kombu_message schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'kombu_message';

-- Result:
-- id: integer (NO)
-- visible: boolean (NO)
-- timestamp: timestamp without time zone (YES)
-- payload: text (NO)
-- version: smallint (NO)
-- queue_id: integer (NO)
```

### Queue Depth Query (Read-Only)

```sql
SELECT
    q.name AS queue_name,
    SUM(CASE WHEN m.visible THEN 1 ELSE 0 END) AS visible_count,
    SUM(CASE WHEN NOT m.visible THEN 1 ELSE 0 END) AS invisible_count,
    COUNT(*) AS total
FROM kombu_queue q
LEFT JOIN kombu_message m ON m.queue_id = q.id
WHERE q.name NOT LIKE '%.reply.celery.pidbox'
GROUP BY q.name
ORDER BY q.name;

-- Sample result:
-- attribution     | 0 | 0 | 1
-- housekeeping    | 0 | 0 | 1
-- llm             | 0 | 0 | 1
-- maintenance     | 0 | 204 | 204
```

### Max Age Query (Read-Only)

```sql
SELECT
    q.name AS queue_name,
    MIN(m.timestamp) AS oldest_message,
    MAX(m.timestamp) AS newest_message,
    EXTRACT(EPOCH FROM (NOW() - MIN(m.timestamp))) AS max_age_seconds
FROM kombu_queue q
LEFT JOIN kombu_message m ON m.queue_id = q.id
WHERE q.name NOT LIKE '%.reply.celery.pidbox'
  AND m.timestamp IS NOT NULL
GROUP BY q.name
ORDER BY q.name;

-- Sample result:
-- maintenance | 2026-01-15 20:37:28 | 2026-01-15 20:39:21 | 221
```

### Ambiguity Notes

1. **Enqueue time**: `kombu_message.timestamp` represents message enqueue time
2. **ETA/countdown**: Stored in payload JSON `headers.eta` field, not a separate column
3. **Reservation**: `visible=false` indicates message is reserved (being processed)
4. **Age calculation**: `NOW() - MIN(timestamp)` gives max wait time for visible messages; invisible messages are being processed

---

## 6. Drift Delta Map

| Aspect | B0.5.6 Intended | Current Reality | Delta |
|--------|-----------------|-----------------|-------|
| Worker-side HTTP server exists? | TBD (Phase 5 controls) | **YES** - wsgiref on port 9540 | Active but unintended |
| Uses sockets / wsgiref? | No sockets (hermetic) | **YES** - transitive via wsgiref→socketserver | Scanner bypass |
| Runs per process and binds port deterministically? | N/A | **NO** - multiple workers can bind same port on Windows | Port conflict risk |
| `/metrics` exists on worker? | TBD | **YES** - prometheus_client WSGI app | Exposed |
| `/metrics` exists on API? | TBD | **YES** - generate_latest() via FastAPI | Exposed |
| Metrics registry unified or split? | Should be unified | **SPLIT** - process-local registries | Data fragmentation |
| `/health` checks do data-plane round-trip? | Should be data-plane | **NO** - connectivity only (SELECT 1) | Shallow checks |
| Any auth/allowlist? | Should have auth | **NONE** - open endpoints | Security gap |
| Any sensitive labels/values exposed? | None | **YES** - `tenant_id` in event metrics labels | PII exposure risk |

---

## 7. Open Questions That Block Implementation

1. **Decision needed**: Should worker-side HTTP server be removed, hardened (auth + bind to 127.0.0.1), or relocated to API?

2. **Registry unification**: If keeping both surfaces, how to aggregate worker metrics into API `/metrics` endpoint? Options:
   - Push gateway
   - Multi-target Prometheus scraping
   - Remove worker-side, expose via API only

3. **Port conflict resolution**: For multi-worker deployments:
   - Assign unique ports per worker via env var or auto-increment?
   - Use Unix domain sockets instead?
   - Remove worker HTTP server entirely?

4. **Hermetic scanner enhancement**: Should scanner be extended to detect transitive socket usage via stdlib modules?

5. **Sensitive label policy**: Should `tenant_id` be removed from metric labels or is it acceptable for internal metrics?

---

## Exit Gate Summary

| Gate | Status | Evidence |
|------|--------|----------|
| G-DRIFT-BIND | **PASS** | Port 9540 binds at runtime; concurrency>1 creates conflicts on Windows |
| G-SURFACES | **PASS** | Complete inventory in Section 3 endpoint table |
| G-TELEMETRY-CONTENTS | **PASS** | `/metrics` sampled; `tenant_id` label identified |
| G-HEALTH-SEMANTICS | **PASS** | Worker: broker+DB connectivity; API: DB+RLS validation |
| G-BROKER-TRUTH | **PASS** | `sqla+postgresql://`, kombu tables documented, queries provided |
| G-HERMETIC-NUANCE | **PASS** | wsgiref→http.server→socketserver→socket chain documented |
| G-DELTA-MAP | **PASS** | Section 6 delta table complete |

---

**End of Evidence Pack**
