"""
B0.5.6.5: Canonical runtime config for worker/task metrics topology.

This module is deliberately dependency-light:
- Reads ONLY environment variables (no app.settings, no DB/Celery imports).
- Provides a single authority for PROMETHEUS_MULTIPROC_DIR and exporter bind config.
- Fails fast if multiprocess directory is missing/misconfigured.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# Canonical error message (tests assert this exact string).
MULTIPROC_DIR_INVALID_ERROR = (
    "B0.5.6.5: PROMETHEUS_MULTIPROC_DIR must be an absolute path to an existing, "
    "writable/executable directory provisioned externally; the app will not create it."
)


def _get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _get_int_env(name: str, default: int) -> int:
    raw = _get_env(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid {name} (must be int)") from exc
    if value < 0:
        raise RuntimeError(f"Invalid {name} (must be >= 0)")
    return value


def get_multiproc_dir() -> Path:
    raw = _get_env("PROMETHEUS_MULTIPROC_DIR")
    if raw is None:
        raise RuntimeError(MULTIPROC_DIR_INVALID_ERROR)
    path = Path(raw)
    validate_multiproc_dir(path)
    return path


def validate_multiproc_dir(path: Path) -> None:
    if not path.is_absolute():
        raise RuntimeError(MULTIPROC_DIR_INVALID_ERROR)
    if not path.exists() or not path.is_dir():
        raise RuntimeError(MULTIPROC_DIR_INVALID_ERROR)

    # Directory traversal (X) + write access (W) are required for multiprocess shard I/O.
    #
    # Note: We intentionally do not create/delete probe files here; the exporter must be
    # read-only with respect to shard files, and validation should not mutate the directory.
    if not os.access(path, os.W_OK | os.X_OK):
        raise RuntimeError(MULTIPROC_DIR_INVALID_ERROR)


@dataclass(frozen=True, slots=True)
class WorkerMetricsExporterBind:
    host: str
    port: int


def get_worker_metrics_exporter_bind() -> WorkerMetricsExporterBind:
    host = _get_env("WORKER_METRICS_EXPORTER_HOST") or "127.0.0.1"
    port = _get_int_env("WORKER_METRICS_EXPORTER_PORT", 9108)
    return WorkerMetricsExporterBind(host=host, port=port)


@dataclass(frozen=True, slots=True)
class MultiprocPrunePolicy:
    grace_seconds: int
    interval_seconds: int
    max_shard_files: int


def get_multiproc_prune_policy() -> MultiprocPrunePolicy:
    return MultiprocPrunePolicy(
        grace_seconds=_get_int_env("PROMETHEUS_MULTIPROC_PRUNE_GRACE_SECONDS", 600),
        interval_seconds=_get_int_env("PROMETHEUS_MULTIPROC_PRUNE_INTERVAL_SECONDS", 60),
        max_shard_files=_get_int_env("PROMETHEUS_MULTIPROC_MAX_SHARD_FILES", 10_000),
    )

