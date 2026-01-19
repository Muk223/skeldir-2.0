"""
Prometheus metrics emitted by the FastAPI application process (API-only).

B0.5.6.7 topology guardrail:
- API `/metrics` must not expose worker task metrics.
- Worker task metrics are emitted by the Celery worker into Prometheus multiprocess shards
  and are exposed ONLY via `app.observability.worker_metrics_exporter`.

This module intentionally contains only API-side metrics (ingestion/event flow). Worker/task
metrics live in `app.observability.metrics`.
"""

from prometheus_client import Counter, Histogram


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

