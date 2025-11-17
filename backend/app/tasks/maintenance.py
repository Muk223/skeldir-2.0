"""
Maintenance Background Tasks

This module implements Celery tasks for database maintenance operations, including:
- Materialized view refresh automation (Phase 6 of B0.3)
- PII audit scanning (Phase 4 of Privacy Governance)
- Data retention enforcement (Phase 5 of Privacy Governance)

Contract: Maintenance tasks must run at defined intervals to meet SLOs and governance requirements.

Related Documents:
- docs/database/Database_Schema_Functional_Implementation_Plan.md (Phase 6)
- docs/governance/PRIVACY_LIFECYCLE_IMPLEMENTATION.md (Phases 4-5)
- .cursor/rules (Celery with PostgreSQL broker pattern)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict

from celery import shared_task
from celery.schedules import crontab
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

# Materialized views that require refresh automation
MATERIALIZED_VIEWS = [
    "mv_channel_performance",
    "mv_daily_revenue_summary",
]

# Database connection (to be configured via environment)
# TODO: Load from environment variables or config
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/skeldir"


@shared_task(
    bind=True,
    name="app.tasks.maintenance.refresh_all_materialized_views",
    max_retries=3,
    default_retry_delay=60
)
def refresh_all_materialized_views_task(self):
    """
    Celery task to refresh all materialized views using CONCURRENTLY mode.
    
    This task:
    1. Iterates through all materialized views in MATERIALIZED_VIEWS
    2. Executes `REFRESH MATERIALIZED VIEW CONCURRENTLY` for each view
    3. Logs refresh duration and row counts for monitoring
    
    Schedule: Every 5 minutes via Celery Beat (crontab(minute="*/5"))
    
    Note: This task runs under a trusted role (migration_owner or direct connection)
    and does NOT require tenant context, as it refreshes views for all tenants.
    
    Returns:
        dict: Refresh results with view names, durations, and status
    """
    engine: AsyncEngine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    results = {}
    
    try:
        async with SessionLocal() as session:
            for view_name in MATERIALIZED_VIEWS:
                try:
                    logger.info(
                        "Refreshing materialized view",
                        extra={"view_name": view_name, "task_id": self.request.id}
                    )
                    
                    # Record start time
                    start_time = self.request.id  # Use task ID as timestamp proxy
                    # TODO: Use actual timestamp from time module
                    
                    # Execute REFRESH MATERIALIZED VIEW CONCURRENTLY
                    await session.execute(
                        text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                    )
                    await session.commit()
                    
                    # Log success
                    logger.info(
                        "Materialized view refreshed successfully",
                        extra={
                            "view_name": view_name,
                            "task_id": self.request.id,
                            "event_type": "matview_refresh_success"
                        }
                    )
                    
                    results[view_name] = {"status": "success"}
                    
                except Exception as e:
                    logger.error(
                        "Failed to refresh materialized view",
                        extra={
                            "view_name": view_name,
                            "task_id": self.request.id,
                            "error": str(e),
                            "event_type": "matview_refresh_failure"
                        },
                        exc_info=True
                    )
                    results[view_name] = {"status": "error", "error": str(e)}
                    
                    # Retry individual view refresh on failure
                    raise self.retry(exc=e, countdown=60)
        
        return results
        
    except Exception as e:
        logger.error(
            "Materialized view refresh task failed",
            extra={"task_id": self.request.id, "error": str(e)},
            exc_info=True
        )
        raise self.retry(exc=e, countdown=60)
    
    finally:
        await engine.dispose()


@shared_task(
    bind=True,
    name="app.tasks.maintenance.scan_for_pii_contamination",
    max_retries=3,
    default_retry_delay=60
)
def scan_for_pii_contamination_task(self):
    """
    Celery task to run PII audit scan and alert on findings.
    
    This task:
    1. Executes fn_scan_pii_contamination() database function
    2. Checks for recent findings (last 25 hours)
    3. Logs CRITICAL alert if findings detected
    4. Returns finding counts for monitoring
    
    Schedule: Daily at 4:00 AM UTC via Celery Beat
    
    Related Documents:
    - docs/governance/PRIVACY_LIFECYCLE_IMPLEMENTATION.md (Phase 4)
    - docs/database/pii-controls.md (Layer 3 audit)
    
    Returns:
        dict: Finding counts (finding_count, recent_findings)
    """
    engine: AsyncEngine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    try:
        async with SessionLocal() as session:
            # Execute audit scan function
            result = await session.execute(
                text("SELECT fn_scan_pii_contamination();")
            )
            finding_count = result.scalar()
            await session.commit()
            
            # Check findings from last 25 hours (to catch recent contamination)
            recent_result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM pii_audit_findings 
                    WHERE detected_at > NOW() - INTERVAL '25 hours'
                """)
            )
            recent_findings = recent_result.scalar()
            
            if recent_findings > 0:
                message = f"CRITICAL: {recent_findings} new PII findings detected. Immediate review required."
                logger.critical(
                    message,
                    extra={
                        "finding_count": finding_count,
                        "recent_findings": recent_findings,
                        "task_id": self.request.id,
                        "event_type": "pii_audit_failure"
                    }
                )
                # TODO: Implement send_security_alert_email() or use existing alerting
                # send_security_alert_email(subject="PII AUDIT FAILURE", body=message)
            
            logger.info(
                "PII audit scan completed",
                extra={
                    "finding_count": finding_count,
                    "recent_findings": recent_findings,
                    "task_id": self.request.id,
                    "event_type": "pii_audit_success"
                }
            )
            
            return {
                "finding_count": finding_count,
                "recent_findings": recent_findings
            }
    
    except Exception as e:
        logger.error(
            "PII audit scan failed",
            extra={
                "error": str(e),
                "task_id": self.request.id,
                "event_type": "pii_audit_error"
            },
            exc_info=True
        )
        raise self.retry(exc=e, countdown=60)
    
    finally:
        await engine.dispose()


@shared_task(
    bind=True,
    name="app.tasks.maintenance.enforce_data_retention",
    max_retries=3,
    default_retry_delay=60
)
def enforce_data_retention_task(self):
    """
    Celery task to enforce 90-day retention policy for analytics data.
    
    This task:
    1. Deletes old analytics data (attribution_events, attribution_allocations) older than 90 days
    2. Deletes old, resolved transient data (dead_events) older than 30 days post-resolution
    3. Preserves financial audit data (revenue_ledger, revenue_state_transitions)
    4. Logs deletion counts for monitoring
    
    Schedule: Daily at 3:00 AM UTC via Celery Beat (before PII audit at 4 AM)
    
    Note: Respects RLS (deletion is tenant-scoped via RLS policies)
    
    Related Documents:
    - docs/governance/PRIVACY_LIFECYCLE_IMPLEMENTATION.md (Phase 5)
    - B0.3_FORENSIC_ANALYSIS_RESPONSE.md (retention gap identified)
    
    Returns:
        dict: Deletion counts (events_deleted, allocations_deleted, dead_events_deleted)
    """
    engine: AsyncEngine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    cutoff_90_day = datetime.now(timezone.utc) - timedelta(days=90)
    cutoff_30_day = datetime.now(timezone.utc) - timedelta(days=30)
    
    try:
        async with SessionLocal() as session:
            # 1. Delete old analytics data (90-day retention)
            events_result = await session.execute(
                text("DELETE FROM attribution_events WHERE event_timestamp < :cutoff"),
                {'cutoff': cutoff_90_day}
            )
            events_deleted = events_result.rowcount
            
            allocations_result = await session.execute(
                text("DELETE FROM attribution_allocations WHERE created_at < :cutoff"),
                {'cutoff': cutoff_90_day}
            )
            allocations_deleted = allocations_result.rowcount
            
            # 2. Delete old, resolved transient data (30-day post-resolution)
            dead_events_result = await session.execute(
                text("""
                    DELETE FROM dead_events 
                    WHERE remediation_status IN ('resolved', 'abandoned') 
                    AND resolved_at < :cutoff
                """),
                {'cutoff': cutoff_30_day}
            )
            dead_events_deleted = dead_events_result.rowcount
            
            await session.commit()
            
            logger.info(
                "Data retention enforcement completed",
                extra={
                    "events_deleted": events_deleted,
                    "allocations_deleted": allocations_deleted,
                    "dead_events_deleted": dead_events_deleted,
                    "cutoff_90_day": cutoff_90_day.isoformat(),
                    "cutoff_30_day": cutoff_30_day.isoformat(),
                    "task_id": self.request.id,
                    "event_type": "retention_enforcement_success"
                }
            )
            
            return {
                "events_deleted": events_deleted,
                "allocations_deleted": allocations_deleted,
                "dead_events_deleted": dead_events_deleted
            }
    
    except Exception as e:
        logger.error(
            "Data retention enforcement failed",
            extra={
                "error": str(e),
                "task_id": self.request.id,
                "event_type": "retention_enforcement_error"
            },
            exc_info=True
        )
        raise self.retry(exc=e, countdown=60)
    
    finally:
        await engine.dispose()


# Celery Beat schedule configuration
# This should be added to celery_app.conf.beat_schedule in app/core/celery_app.py
BEAT_SCHEDULE = {
    "refresh-matviews-every-5-min": {
        "task": "app.tasks.maintenance.refresh_all_materialized_views",
        "schedule": 300.0,  # 5 minutes in seconds
        "options": {"expires": 300}  # Task expires after 5 minutes
    },
    # PII audit scanner (daily at 4:00 AM UTC)
    "pii-audit-scanner": {
        "task": "app.tasks.maintenance.scan_for_pii_contamination",
        "schedule": crontab(hour=4, minute=0),  # Daily at 4:00 AM UTC
        "options": {"expires": 3600}  # Task expires after 1 hour
    },
    # Data retention enforcement (daily at 3:00 AM UTC, before PII audit at 4 AM)
    "enforce-data-retention": {
        "task": "app.tasks.maintenance.enforce_data_retention",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM UTC
        "options": {"expires": 3600}  # Task expires after 1 hour
    }
}

