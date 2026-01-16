"""
Health probe tasks for data-plane worker capability checks (B0.5.6.2).

Provides a deterministic Celery task used by /health/worker to prove:
- API -> broker -> worker -> result backend -> API round trip
- Worker can access the database
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import psycopg2
from sqlalchemy import text
from sqlalchemy.engine.url import make_url

from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import engine
from app.observability.context import set_request_correlation_id, set_tenant_id

logger = logging.getLogger(__name__)


def _run_coro(coro):
    """
    Run an async coroutine from sync context, even if an event loop is running.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()


async def _fetch_db_user() -> str:
    """
    Execute a trivial query to prove the worker connects with the DB role.
    """
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT current_user"))
        return res.scalar() or ""


def _fetch_db_user_sync() -> str:
    """
    Sync path for DB user check using psycopg2 (avoids event loop conflicts).
    """
    url = make_url(settings.DATABASE_URL.unicode_string())
    query = dict(url.query)
    query.pop("channel_binding", None)
    url = url.set(query=query)
    if url.drivername.startswith("postgresql+"):
        url = url.set(drivername="postgresql")

    dsn_parts = ["postgresql://"]
    if url.username:
        dsn_parts.append(url.username)
        if url.password:
            dsn_parts.append(":")
            dsn_parts.append(url.password)
        dsn_parts.append("@")
    dsn_parts.append(url.host or "localhost")
    if url.port:
        dsn_parts.append(f":{url.port}")
    if url.database:
        dsn_parts.append(f"/{url.database}")
    dsn = "".join(dsn_parts)

    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT current_user")
        return cur.fetchone()[0]
    finally:
        conn.close()


@celery_app.task(bind=True, name="app.tasks.health.probe", routing_key="housekeeping.task")
def probe(self) -> dict:
    """
    Deterministic worker probe for /health/worker data-plane validation.
    """
    correlation_id = getattr(self.request, "correlation_id", None) or str(uuid4())
    set_request_correlation_id(correlation_id)
    try:
        logger.info(
            "health_probe_start",
            extra={"task_name": self.name, "task_id": self.request.id, "correlation_id": correlation_id},
        )
        try:
            db_user = _fetch_db_user_sync()
        except Exception:
            db_user = _run_coro(_fetch_db_user())

        payload = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "db_user": db_user,
            "worker": getattr(self.request, "hostname", None),
            "task_id": self.request.id,
        }
        logger.info(
            "health_probe_success",
            extra={"task_name": self.name, "task_id": self.request.id, "db_user": db_user},
        )
        return payload
    finally:
        set_request_correlation_id(None)
        set_tenant_id(None)
