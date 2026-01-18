"""
Prometheus metrics definitions with bounded cardinality (B0.5.6.3).

All labels MUST be constrained to closed sets defined in metrics_policy.py.
No tenant_id, UUID, or unbounded user-supplied values are permitted.

Label policy enforcement:
- Event metrics: No labels (aggregate counters only)
- Celery task metrics: task_name only (bounded by ALLOWED_TASK_NAMES)
- Matview metrics: view_name + outcome (bounded by ALLOWED_VIEW_NAMES × ALLOWED_OUTCOMES)

Multiprocess Mode (B0.5.6.3):
    For pre-forked environments (Uvicorn workers, Gunicorn, Celery), set
    PROMETHEUS_MULTIPROC_DIR to a writable directory BEFORE any prometheus_client
    imports. Each worker process will write metrics to files in this directory,
    and the /metrics endpoint aggregates them via MultiProcessCollector.
    
    Example:
        export PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
        mkdir -p $PROMETHEUS_MULTIPROC_DIR
        uvicorn app.main:app --workers 4
    
    Without PROMETHEUS_MULTIPROC_DIR, metrics are process-local and only the
    worker handling the /metrics scrape will report its own values.
"""
from prometheus_client import Counter, Histogram


# =============================================================================
# Event Ingestion Metrics (B0.5.6.3: No labels - aggregate only)
# =============================================================================
# Removed: tenant_id, vendor, event_type, error_type labels
# Rationale: tenant_id is PII/unbounded; vendor/event_type/error_type are
# unbounded strings. Detailed diagnostics belong in logs/traces, not metrics.

events_ingested_total = Counter(
    "events_ingested_total",
    "Total successfully ingested events",
)

events_duplicate_total = Counter(
    "events_duplicate_total",
    "Total duplicate events detected by idempotency",
)

events_dlq_total = Counter(
    "events_dlq_total",
    "Total events routed to DLQ",
)

ingestion_duration_seconds = Histogram(
    "ingestion_duration_seconds",
    "Ingestion duration per event",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)


# =============================================================================
# Celery Task Metrics (B0.5.6.3: task_name only)
# =============================================================================
# Label: task_name - bounded by ALLOWED_TASK_NAMES in metrics_policy.py

celery_task_started_total = Counter(
    "celery_task_started_total",
    "Total Celery tasks started",
    ["task_name"],
)

celery_task_success_total = Counter(
    "celery_task_success_total",
    "Total Celery tasks succeeded",
    ["task_name"],
)

celery_task_failure_total = Counter(
    "celery_task_failure_total",
    "Total Celery tasks failed",
    ["task_name"],
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Duration of Celery tasks in seconds",
    ["task_name"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)


# =============================================================================
# Materialized View Refresh Metrics (B0.5.6.3: view_name + outcome)
# =============================================================================
# Labels: view_name, outcome - bounded by ALLOWED_VIEW_NAMES × ALLOWED_OUTCOMES
# Removed: strategy, error_type (unbounded strings)

matview_refresh_total = Counter(
    "matview_refresh_total",
    "Total materialized view refresh attempts",
    ["view_name", "outcome"],
)

matview_refresh_duration_seconds = Histogram(
    "matview_refresh_duration_seconds",
    "Materialized view refresh duration in seconds",
    ["view_name", "outcome"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)

matview_refresh_failures_total = Counter(
    "matview_refresh_failures_total",
    "Materialized view refresh failures",
    ["view_name", "outcome"],
)
