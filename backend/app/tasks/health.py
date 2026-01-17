"""
Health probe task for end-to-end worker capability validation (B0.5.6.2).

This task is invoked by /health/worker to prove the data-plane round trip:
API -> broker -> worker -> result backend -> API.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import text

from app.celery_app import celery_app
from app.db.session import engine
from app.observability.context import set_request_correlation_id

logger = logging.getLogger(__name__)


def _run_coro(coro):
    """
    Run an async coroutine from sync context, even if an event loop is running.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()


async def _fetch_db_user() -> str:
    """
    Execute a trivial query to prove DB connectivity from the worker.
    """
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT current_user"))
        return res.scalar() or ""


@celery_app.task(bind=True, name="app.tasks.health.probe", routing_key="housekeeping.health")
def probe(self) -> dict:
    """
    Health probe task used by /health/worker.
    """
    correlation_id = getattr(self.request, "correlation_id", None) or str(uuid4())
    set_request_correlation_id(correlation_id)
    try:
        logger.info(
            "health_probe_task_start",
            extra={"task_name": self.name, "task_id": self.request.id, "correlation_id": correlation_id},
        )
        db_user: Optional[str] = None
        try:
            db_user = _run_coro(_fetch_db_user())
        except Exception:
            logger.exception("health_probe_db_check_failed")
        payload = {
            "status": "ok" if db_user else "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "db_user": db_user,
            "worker": getattr(self.request, "hostname", None),
        }
        logger.info(
            "health_probe_task_complete",
            extra={
                "task_name": self.name,
                "task_id": self.request.id,
                "db_user": db_user,
                "correlation_id": correlation_id,
            },
        )
        return payload
    finally:
        set_request_correlation_id(None)
