"""
Lightweight HTTP server for Celery worker metrics and health checks.

Exposes Prometheus metrics from the default registry and a /health endpoint
that validates broker and database connectivity under the current Celery config.
"""

import json
import logging
import threading
from typing import Optional, Callable

from prometheus_client import make_wsgi_app
from wsgiref.simple_server import make_server, WSGIServer

from app.db.session import validate_database_connection

logger = logging.getLogger(__name__)

_server_started = False
_server_lock = threading.Lock()


def _check_broker(celery_app) -> bool:
    """
    Attempt a short-lived broker connection to validate connectivity.
    """
    try:
        with celery_app.connection_for_read() as conn:
            conn.ensure_connection(max_retries=1)
        return True
    except Exception as exc:  # pragma: no cover - best effort probe
        logger.error("celery_broker_health_check_failed", exc_info=exc)
        return False


def _check_database() -> bool:
    """
    Validate database connectivity using shared engine helpers.
    """
    try:
        # validate_database_connection raises on failure
        import asyncio

        asyncio.run(validate_database_connection())
        return True
    except Exception as exc:  # pragma: no cover - best effort probe
        logger.error("celery_db_health_check_failed", exc_info=exc)
        return False


def _build_app(celery_app) -> Callable:
    """
    Build a WSGI app that serves /metrics and /health.
    """
    metrics_app = make_wsgi_app()

    def application(environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path == "/metrics":
            return metrics_app(environ, start_response)

        if path == "/health":
            broker_ok = _check_broker(celery_app)
            db_ok = _check_database()
            healthy = broker_ok and db_ok
            status = "200 OK" if healthy else "503 Service Unavailable"
            payload = json.dumps(
                {
                    "status": "ok" if healthy else "unhealthy",
                    "broker": "ok" if broker_ok else "error",
                    "database": "ok" if db_ok else "error",
                }
            ).encode()
            headers = [("Content-Type", "application/json"), ("Content-Length", str(len(payload)))]
            start_response(status, headers)
            return [payload]

        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"not found"]

    return application


def start_worker_http_server(celery_app, host: str, port: int) -> Optional[threading.Thread]:
    """
    Start a background HTTP server exposing worker metrics and health.

    Guarded to start only once per worker process.
    """
    global _server_started
    with _server_lock:
        if _server_started:
            return None
        _server_started = True

    app = _build_app(celery_app)

    def _run():
        try:
            with make_server(host, port, app, server_class=WSGIServer) as httpd:
                logger.info("celery_worker_metrics_server_started", extra={"host": host, "port": port})
                httpd.serve_forever()
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error(
                "celery_worker_metrics_server_failed",
                exc_info=exc,
                extra={"host": host, "port": port},
            )

    thread = threading.Thread(target=_run, name="celery-worker-metrics", daemon=True)
    thread.start()
    return thread
