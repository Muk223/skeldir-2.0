"""
B0.5.6.5: Read-only Prometheus exporter for worker/task metrics (multiprocess mode).

Topology invariants:
- Exporter is the only HTTP listener for worker metrics.
- Exporter is strictly read-only w.r.t. PROMETHEUS_MULTIPROC_DIR (no wipes/deletes).
- Exporter must not import app settings, SQLAlchemy, Celery, or any DB-initializing code.
"""

from __future__ import annotations

import os
from wsgiref.simple_server import WSGIRequestHandler, make_server

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector

from app.observability.metrics_runtime_config import (
    get_multiproc_dir,
    get_worker_metrics_exporter_bind,
)


def _build_wsgi_app():
    multiproc_dir = get_multiproc_dir()
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = str(multiproc_dir)

    registry = CollectorRegistry()
    MultiProcessCollector(registry)

    def app(environ, start_response):
        path = environ.get("PATH_INFO") or ""
        if path != "/metrics":
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
            return [b"Not Found"]

        data = generate_latest(registry)
        start_response("200 OK", [("Content-Type", CONTENT_TYPE_LATEST)])
        return [data]

    return app


class _NoLoggingHandler(WSGIRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - signature required by base class
        return


def run() -> None:
    bind = get_worker_metrics_exporter_bind()
    httpd = make_server(bind.host, bind.port, _build_wsgi_app(), handler_class=_NoLoggingHandler)
    httpd.serve_forever()


if __name__ == "__main__":
    run()

