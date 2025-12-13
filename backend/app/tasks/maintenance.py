"""
Maintenance Background Tasks

Foundation-level maintenance tasks executed by Celery workers. These tasks are
intentionally minimal but syntactically correct, RLS-aware, and wired to the
shared configuration (Postgres-only broker/backend).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from celery.schedules import crontab
from sqlalchemy import text

from app.celery_app import celery_app
from app.db.session import engine, set_tenant_guc
from app.observability.context import set_request_correlation_id, set_tenant_id
from app.tasks.context import tenant_task

logger = logging.getLogger(__name__)

# Materialized views that require refresh automation
MATERIALIZED_VIEWS: List[str] = [
    "mv_channel_performance",
    "mv_daily_revenue_summary",
]


async def _refresh_view(view_name: str, task_id: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
        logger.info(
            "matview_refreshed",
            extra={"view_name": view_name, "task_id": task_id},
        )


@celery_app.task(
    bind=True,
    name="app.tasks.maintenance.refresh_all_materialized_views",
    routing_key="maintenance.task",
    max_retries=3,
    default_retry_delay=60,
)
def refresh_all_materialized_views_task(self) -> Dict[str, str]:
    """
    Refresh configured materialized views. Global (non-tenant) scope.
    """
    correlation_id = getattr(self.request, "correlation_id", None) or str(uuid4())
    set_request_correlation_id(correlation_id)
    results: Dict[str, str] = {}
    try:
        for view_name in MATERIALIZED_VIEWS:
            asyncio.run(_refresh_view(view_name, self.request.id))
            results[view_name] = "success"
        return results
    except Exception as exc:
        logger.error(
            "matview_refresh_failed",
            exc_info=exc,
            extra={"task_id": self.request.id, "correlation_id": correlation_id},
        )
        raise self.retry(exc=exc, countdown=60)
    finally:
        set_request_correlation_id(None)


async def _validate_db_connection_for_tenant(tenant_id: UUID) -> str:
    async with engine.begin() as conn:
        await set_tenant_guc(conn, tenant_id, local=False)
        res = await conn.execute(text("SELECT current_setting('app.current_tenant_id')"))
        return res.scalar() or ""


@celery_app.task(
    bind=True,
    name="app.tasks.maintenance.scan_for_pii_contamination",
    max_retries=3,
    default_retry_delay=60,
)
@tenant_task
def scan_for_pii_contamination_task(self, tenant_id: UUID, correlation_id: Optional[str] = None) -> Dict[str, str]:
    """
    Stub PII scan task; validates connectivity and tenant context.
    """
    correlation_id = correlation_id or str(uuid4())
    set_request_correlation_id(correlation_id)
    set_tenant_id(tenant_id)
    try:
        current = asyncio.run(_validate_db_connection_for_tenant(tenant_id))
        logger.info(
            "pii_scan_stub_completed",
            extra={"tenant_id": str(tenant_id), "task_id": self.request.id, "correlation_id": correlation_id},
        )
        return {"status": "ok", "tenant_id": str(tenant_id), "guc": current}
    except Exception as exc:
        logger.error(
            "pii_scan_stub_failed",
            exc_info=exc,
            extra={"tenant_id": str(tenant_id), "task_id": self.request.id, "correlation_id": correlation_id},
        )
        raise self.retry(exc=exc, countdown=60)


async def _enforce_retention(tenant_id: UUID, cutoff_90: datetime, cutoff_30: datetime) -> Dict[str, int]:
    async with engine.begin() as conn:
        await set_tenant_guc(conn, tenant_id, local=False)
        events_deleted = (await conn.execute(text("DELETE FROM attribution_events WHERE event_timestamp < :cutoff"), {"cutoff": cutoff_90})).rowcount or 0
        allocations_deleted = (await conn.execute(text("DELETE FROM attribution_allocations WHERE created_at < :cutoff"), {"cutoff": cutoff_90})).rowcount or 0
        dead_events_deleted = (
            await conn.execute(
                text(
                    """
                    DELETE FROM dead_events
                    WHERE remediation_status IN ('resolved', 'abandoned')
                    AND resolved_at < :cutoff
                    """
                ),
                {"cutoff": cutoff_30},
            )
        ).rowcount or 0
        return {
            "events_deleted": events_deleted,
            "allocations_deleted": allocations_deleted,
            "dead_events_deleted": dead_events_deleted,
        }


@celery_app.task(
    bind=True,
    name="app.tasks.maintenance.enforce_data_retention",
    max_retries=3,
    default_retry_delay=60,
)
@tenant_task
def enforce_data_retention_task(self, tenant_id: UUID, correlation_id: Optional[str] = None) -> Dict[str, int]:
    """
    Tenant-scoped retention enforcement with RLS guardrails.
    """
    correlation_id = correlation_id or str(uuid4())
    set_request_correlation_id(correlation_id)
    set_tenant_id(tenant_id)
    cutoff_90_day = datetime.now(timezone.utc) - timedelta(days=90)
    cutoff_30_day = datetime.now(timezone.utc) - timedelta(days=30)
    try:
        results = asyncio.run(_enforce_retention(tenant_id, cutoff_90_day, cutoff_30_day))
        logger.info(
            "retention_enforced",
            extra={
                "tenant_id": str(tenant_id),
                "task_id": self.request.id,
                "correlation_id": correlation_id,
                **results,
            },
        )
        return results
    except Exception as exc:
        logger.error(
            "retention_enforcement_failed",
            exc_info=exc,
            extra={"tenant_id": str(tenant_id), "task_id": self.request.id, "correlation_id": correlation_id},
        )
        raise self.retry(exc=exc, countdown=60)


# Celery Beat schedule configuration (reference)
BEAT_SCHEDULE = {
    "refresh-matviews-every-5-min": {
        "task": "app.tasks.maintenance.refresh_all_materialized_views",
        "schedule": 300.0,  # 5 minutes
        "options": {"expires": 300},
    },
    "pii-audit-scanner": {
        "task": "app.tasks.maintenance.scan_for_pii_contamination",
        "schedule": crontab(hour=4, minute=0),
        "options": {"expires": 3600},
    },
    "enforce-data-retention": {
        "task": "app.tasks.maintenance.enforce_data_retention",
        "schedule": crontab(hour=3, minute=0),
        "options": {"expires": 3600},
    },
}
