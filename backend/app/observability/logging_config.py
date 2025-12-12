"""
Structured logging configuration.

Uses JSON-formatted logs with correlation_id and tenant_id context.
"""
import json
import logging
from typing import Any, Dict

from app.observability.context import (
    get_request_correlation_id,
    get_business_correlation_id,
    get_tenant_id,
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include correlation and tenant context if available
        cid_req = getattr(record, "correlation_id_request", None) or get_request_correlation_id()
        cid_bus = getattr(record, "correlation_id_business", None) or get_business_correlation_id()
        tid = getattr(record, "tenant_id", None) or get_tenant_id()
        if cid_req:
            log["correlation_id_request"] = cid_req
        if cid_bus:
            log["correlation_id_business"] = cid_bus
        if tid:
            log["tenant_id"] = tid
        if record.exc_info:
            log["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), handlers=[handler], force=True)
