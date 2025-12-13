"""
Tenant context helpers for Celery tasks.

Provides a decorator that enforces tenant_id presence, sets contextvars for
logging, applies the tenant GUC using the shared engine, and normalizes
correlation IDs for observability.
"""
import asyncio
import functools
import logging
import uuid
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy import text

from app.db.session import engine, set_tenant_guc
from app.observability.context import set_request_correlation_id, set_tenant_id

logger = logging.getLogger(__name__)


def _normalize_tenant_id(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


async def _set_tenant_guc_global(tenant_id: UUID) -> None:
    async with engine.begin() as conn:
        await set_tenant_guc(conn, tenant_id, local=False)
        # Guardrail: read back to prove it stuck for this connection
        await conn.execute(text("SELECT current_setting('app.current_tenant_id')"))


def tenant_task(task_fn: Callable) -> Callable:
    """
    Decorator for tenant-scoped Celery tasks.

    Enforces tenant_id, sets contextvars for logging, applies tenant GUC, and
    guarantees a correlation_id is present for downstream logs/metrics.
    """

    @functools.wraps(task_fn)
    def _wrapped(self, *args, **kwargs):
        tenant_id_value = kwargs.get("tenant_id")
        if tenant_id_value is None:
            raise ValueError("tenant_id is required for tenant-scoped tasks")

        tenant_uuid = _normalize_tenant_id(tenant_id_value)
        correlation_id = kwargs.get("correlation_id") or str(uuid.uuid4())

        set_tenant_id(tenant_uuid)
        set_request_correlation_id(correlation_id)
        kwargs["tenant_id"] = tenant_uuid
        kwargs["correlation_id"] = correlation_id

        try:
            asyncio.run(_set_tenant_guc_global(tenant_uuid))
        except Exception as exc:
            logger.error(
                "celery_tenant_guc_failed",
                exc_info=exc,
                extra={"tenant_id": str(tenant_uuid), "task_name": getattr(self, "name", None)},
            )
            raise

        try:
            return task_fn(self, *args, **kwargs)
        finally:
            # Reset contextvars to avoid leaking across reused worker threads
            set_tenant_id(None)
            set_request_correlation_id(None)

    return _wrapped
