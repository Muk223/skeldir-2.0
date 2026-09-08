"""
R6 Worker Resource Governance - Context Gathering Harness.

Generates SHA-anchored runtime artifacts and minimal probes for worker
governance controls (timeouts, retries, prefetch).

Corrective VIII physics notes (read before changing probe semantics):

* The workflow must establish worker readiness through
  ``scripts/r6/r6_wait_for_worker.py`` (observed task round-trip + live
  parent PID) BEFORE invoking this harness. Elapsed sleep is not readiness
  evidence (``elapsed time != readiness evidence``).
* The prefetch probe measures a BOUNDED-STARVATION invariant (every short
  task starts within 20 s despite long-task pressure), not an exact
  scheduler ordering. Celery does not contractually guarantee completion
  ordering, so assertions stronger than the bound would measure accidental
  timing rather than a production guarantee. Keep the bound loose; tighten
  only if production actually requires a stronger ordering AND the runtime
  is hardened to provide it.
* Remote-control ``inspect`` over the PostgreSQL-backed transport is
  telemetry, not authority: an empty inspect reply with a successful task
  round-trip means the control channel is unreachable, not that the worker
  is absent. Task round-trip plus PID liveness is the authority signal.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4
from urllib.parse import urlsplit

from celery import __version__ as celery_version
from celery.result import AsyncResult

# PYTHONPATH=backend
from app.celery_app import celery_app  # noqa: E402


WORKER_LOG_ENV = "R6_WORKER_LOG_PATH"
PROBE_LOG_ENV = "R6_PROBE_LOG_PATH"
RESULT_GET_TIMEOUT_ENV = "R6_RESULT_GET_TIMEOUT_S"


@dataclass(frozen=True)
class R6Context:
    sha: str
    timestamp_utc: str
    run_url: str
    output_dir: Path
    worker_log_path: Path
    probe_log_path: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_rev_parse_head() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT)
            .decode("utf-8", errors="replace")
            .strip()
        )
    except Exception:
        return "UNKNOWN"


def _git_status_porcelain() -> str:
    try:
        return (
            subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.STDOUT)
            .decode("utf-8", errors="replace")
            .strip()
        )
    except Exception:
        return "UNKNOWN"


def _dsn_scheme_and_hash(dsn: str) -> dict[str, str]:
    if not dsn:
        return {"scheme": "", "sha256": ""}
    parsed = urlsplit(dsn)
    return {"scheme": parsed.scheme, "sha256": sha256(dsn.encode("utf-8")).hexdigest()}


def _write_text(path: Path, content: str, *, sha: str, timestamp: str) -> None:
    header = f"R6_SHA={sha}\nR6_TIMESTAMP_UTC={timestamp}\n"
    path.write_text(header + content, encoding="utf-8")


def _write_json(path: Path, payload: Any, *, sha: str, timestamp: str) -> None:
    if isinstance(payload, dict):
        payload = {"R6_SHA": sha, "R6_TIMESTAMP_UTC": timestamp, **payload}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _run_command(command: list[str]) -> str:
    res = subprocess.run(command, capture_output=True, text=True, check=False)
    return (res.stdout or "") + (res.stderr or "")


def _celery_cli(base_args: list[str]) -> str:
    command = ["celery", "-A", "app.celery_app.celery_app"] + base_args
    return _run_command(command)


def _ensure_output_dir(base_dir: Path, sha: str) -> Path:
    out = base_dir / sha
    out.mkdir(parents=True, exist_ok=True)
    return out


def _read_probe_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _resolve_task_route(task_name: str, routes: dict) -> dict[str, str]:
    for pattern, route in routes.items():
        if fnmatch(task_name, pattern):
            if isinstance(route, dict):
                return {
                    "queue": route.get("queue") or "",
                    "routing_key": route.get("routing_key") or "",
                }
            return {"queue": "", "routing_key": ""}
    return {"queue": "", "routing_key": ""}


def _resolve_task_annotation(task_name: str, annotations: dict) -> dict[str, Any]:
    if not isinstance(annotations, dict):
        return {}
    if task_name in annotations and isinstance(annotations[task_name], dict):
        return annotations[task_name]
    if "*" in annotations and isinstance(annotations["*"], dict):
        return annotations["*"]
    return {}


def _task_governance_matrix() -> list[dict[str, Any]]:
    conf = celery_app.conf
    routes = conf.task_routes or {}
    annotations = conf.task_annotations or {}
    rows: list[dict[str, Any]] = []
    for task_name, task in celery_app.tasks.items():
        if task_name.startswith("celery.") or task_name.startswith("kombu."):
            task_kind = "system"
        else:
            task_kind = "app"

        options = getattr(task, "options", {}) or {}
        route = _resolve_task_route(task_name, routes)
        queue = options.get("queue") or route["queue"] or conf.task_default_queue
        routing_key = options.get("routing_key") or route["routing_key"] or conf.task_default_routing_key

        annotation = _resolve_task_annotation(task_name, annotations)

        max_retries = getattr(task, "max_retries", None)
        retry_backoff = getattr(task, "retry_backoff", None)
        retry_jitter = getattr(task, "retry_jitter", None)
        default_retry_delay = getattr(task, "default_retry_delay", None)
        autoretry_for = getattr(task, "autoretry_for", None)

        time_limit = getattr(task, "time_limit", None) or getattr(conf, "task_time_limit", None)
        soft_time_limit = getattr(task, "soft_time_limit", None) or getattr(
            conf, "task_soft_time_limit", None
        )

        acks_late = getattr(task, "acks_late", None)
        if acks_late is None:
            acks_late = bool(getattr(conf, "task_acks_late", False))
            acks_source = "global"
        else:
            acks_source = "task"

        reject_on_worker_lost = getattr(task, "reject_on_worker_lost", None)
        if reject_on_worker_lost is None:
            reject_on_worker_lost = bool(getattr(conf, "task_reject_on_worker_lost", False))
            reject_source = "global"
        else:
            reject_source = "task"

        retry_source = "missing"
        if max_retries is not None:
            retry_source = "task"
        elif autoretry_for:
            retry_source = "autoretry"
        elif annotation.get("max_retries") is not None:
            max_retries = annotation.get("max_retries")
            retry_source = "annotation"

        if retry_backoff is None:
            retry_backoff = annotation.get("retry_backoff")
        if retry_jitter is None:
            retry_jitter = annotation.get("retry_jitter")
        if default_retry_delay is None:
            default_retry_delay = annotation.get("default_retry_delay")

        rows.append(
            {
                "task_name": task_name,
                "task_kind": task_kind,
                "queue": queue,
                "routing_key": routing_key,
                "max_retries": max_retries,
                "retry_backoff": retry_backoff,
                "retry_jitter": retry_jitter,
                "default_retry_delay": default_retry_delay,
                "autoretry_for": [str(x) for x in (autoretry_for or [])],
                "retry_policy_source": retry_source,
                "time_limit": time_limit,
                "soft_time_limit": soft_time_limit,
                "acks_late": acks_late,
                "acks_source": acks_source,
                "reject_on_worker_lost": reject_on_worker_lost,
                "reject_source": reject_source,
                "acks_on_failure_or_timeout": bool(
                    getattr(conf, "task_acks_on_failure_or_timeout", False)
                ),
            }
        )
    return rows


def _render_task_matrix_md(rows: list[dict[str, Any]]) -> str:
    header = [
        "task_name",
        "task_kind",
        "queue",
        "routing_key",
        "max_retries",
        "retry_backoff",
        "retry_jitter",
        "default_retry_delay",
        "autoretry_for",
        "retry_policy_source",
        "time_limit",
        "soft_time_limit",
        "acks_late",
        "acks_source",
        "reject_on_worker_lost",
        "reject_source",
        "acks_on_failure_or_timeout",
    ]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for row in rows:
        line = []
        for col in header:
            val = row.get(col, "")
            if val is None:
                val = "MISSING"
            line.append(str(val))
        lines.append("| " + " | ".join(line) + " |")
    return "\n".join(lines)


def _build_gap_report(
    snapshot: dict[str, Any],
    matrix_rows: list[dict[str, Any]],
    active_queues: list[str],
) -> str:
    conf = snapshot.get("conf", {})
    missing_retries = [r["task_name"] for r in matrix_rows if r["max_retries"] is None]
    missing_timeouts = [
        r["task_name"] for r in matrix_rows if r["time_limit"] is None or r["soft_time_limit"] is None
    ]
    lines = [
        "# R6 Governance Gap Report",
        "",
        f"- R6_SHA: {snapshot.get('sha')}",
        f"- R6_TIMESTAMP_UTC: {snapshot.get('timestamp_utc')}",
        "",
        "## Required Control Set",
        "",
        f"- task_time_limit: {conf.get('task_time_limit')} (evidence: R6_CELERY_INSPECT_CONF.json)",
        f"- task_soft_time_limit: {conf.get('task_soft_time_limit')} (evidence: R6_CELERY_INSPECT_CONF.json)",
        f"- task_acks_late: {conf.get('task_acks_late')} (evidence: R6_CELERY_INSPECT_CONF.json)",
        f"- task_reject_on_worker_lost: {conf.get('task_reject_on_worker_lost')} (evidence: R6_CELERY_INSPECT_CONF.json)",
        f"- task_acks_on_failure_or_timeout: {conf.get('task_acks_on_failure_or_timeout')} (evidence: R6_CELERY_INSPECT_CONF.json)",
        f"- worker_prefetch_multiplier: {conf.get('worker_prefetch_multiplier')} (evidence: R6_CELERY_INSPECT_CONF.json)",
        f"- worker_max_tasks_per_child: {conf.get('worker_max_tasks_per_child')} (evidence: R6_CELERY_INSPECT_CONF.json)",
        f"- worker_max_memory_per_child: {conf.get('worker_max_memory_per_child')} (evidence: R6_CELERY_INSPECT_CONF.json)",
        "",
        "## Gaps",
        "",
        f"- tasks_missing_retry_caps: {len(missing_retries)}",
        f"- tasks_missing_timeouts: {len(missing_timeouts)}",
        f"- active_queues_observed: {', '.join(active_queues) if active_queues else 'UNKNOWN'}",
    ]
    if missing_retries:
        lines.append(f"- retry_cap_missing_tasks: {', '.join(missing_retries)}")
    if missing_timeouts:
        lines.append(f"- timeout_missing_tasks: {', '.join(missing_timeouts)}")
    return "\n".join(lines) + "\n"


def _pid_alive(pid: object) -> bool:
    """Report whether a worker parent PID is currently alive (Corrective VIII).

    Used to discriminate ``worker never became ready`` from ``worker became
    ready and later disappeared`` and from ``control channel unreachable``.
    """
    try:
        pid_int = int(str(pid))
    except Exception:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True


def _read_parent_pid() -> int | None:
    pidfile = Path(os.getenv("R6_WORKER_PIDFILE", "/tmp/r6_worker.pid"))
    try:
        return int(pidfile.read_text(encoding="utf-8").strip().split()[0])
    except Exception:
        return None


def _dsn_reachable(raw_dsn: str, timeout_s: int = 5) -> tuple[bool, str]:
    """Best-effort broker/result-backend reachability check (scheme + SELECT 1)."""
    dsn = (raw_dsn or "").strip()
    if not dsn:
        return False, "empty-dsn"
    coerced = dsn
    for prefix in ("sqla+postgresql://", "db+postgresql://"):
        if coerced.startswith(prefix):
            coerced = "postgresql://" + coerced[len(prefix):]
    if not coerced.startswith("postgresql"):
        return False, f"non-postgres-scheme:{urlsplit(dsn).scheme}"
    try:
        from sqlalchemy import create_engine, text as sql_text

        engine = create_engine(
            coerced, connect_args={"connect_timeout": int(timeout_s)}
        )
        with engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
        engine.dispose()
        return True, "select-1-ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"{exc.__class__.__name__}:{str(exc)[:200]}"


def _worker_log_tail(path: Path, max_lines: int = 40) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-max_lines:]
    except Exception:
        return []


def _diagnose_result_failure(
    ctx: R6Context,
    *,
    what: str,
    task_id: str | None,
    published_at_utc: str,
    error: str,
) -> dict[str, Any]:
    """Build a causally discriminating failure statement (Corrective VIII §11).

    Replaces a bare ``TimeoutError`` with an evidence bundle permitting an
    independent reader to determine whether the worker never became ready,
    became ready and later disappeared, or remained alive while the
    control/result channel became unreachable.
    """
    parent_pid = _read_parent_pid()
    broker_ok, broker_detail = _dsn_reachable(
        str(getattr(celery_app.conf, "broker_url", "") or "")
    )
    backend_ok, backend_detail = _dsn_reachable(
        str(getattr(celery_app.conf, "result_backend", "") or "")
    )
    try:
        ping = celery_app.control.inspect(timeout=5).ping() or {}
        ping_ok: bool = bool(ping)
        ping_detail = f"replied={len(ping)}"
    except Exception as exc:  # noqa: BLE001
        ping_ok = False
        ping_detail = f"{exc.__class__.__name__}:{str(exc)[:160]}"
    try:
        state = AsyncResult(task_id).state if task_id else "UNKNOWN"
    except Exception:
        state = "UNKNOWN"
    probe_events = _read_probe_events(ctx.probe_log_path)
    diagnosis = {
        "what": what,
        "task_id": task_id,
        "task_published_at_utc": published_at_utc,
        "result_read_at_utc": _utc_now(),
        "error": error,
        "worker_parent_pid": parent_pid,
        "worker_parent_pid_alive": _pid_alive(parent_pid) if parent_pid else False,
        "broker_reachable": broker_ok,
        "broker_detail": broker_detail,
        "result_backend_reachable": backend_ok,
        "result_backend_detail": backend_detail,
        "remote_control_ping_succeeds": ping_ok,
        "remote_control_ping_detail": ping_detail,
        "result_state": state,
        "probe_log_event_count": len(probe_events),
        "worker_log_tail": _worker_log_tail(ctx.worker_log_path),
        "causal_class": (
            "WORKER_NEVER_READY"
            if (not _pid_alive(parent_pid) if parent_pid else True) and not ping_ok
            else "WORKER_DISAPPEARED"
            if parent_pid and not _pid_alive(parent_pid)
            else "CONTROL_OR_RESULT_CHANNEL_UNREACHABLE"
            if not ping_ok
            else "TASK_FAILED_DESPITE_LIVE_WORKER"
        ),
    }
    _write_json(
        ctx.output_dir / "R6_FAILURE_DIAGNOSIS.json",
        diagnosis,
        sha=ctx.sha,
        timestamp=ctx.timestamp_utc,
    )
    print(f"R6_FAILURE_DIAGNOSIS what={what} causal_class={diagnosis['causal_class']}")
    print(f"R6_FAILURE_DIAGNOSIS error={error}")
    return diagnosis


def _causal_get(
    ctx: R6Context, result: Any, *, timeout: float, what: str
) -> Any:
    """Await a Celery result, emitting causal diagnosis instead of bare timeout."""
    task_id = getattr(result, "id", None)
    published_at = _utc_now()
    try:
        value = result.get(timeout=timeout)
        return value
    except Exception as exc:  # noqa: BLE001
        _diagnose_result_failure(
            ctx,
            what=what,
            task_id=task_id,
            published_at_utc=published_at,
            error=f"{exc.__class__.__name__}:{exc}",
        )
        raise


def _readiness_evidence(sha: str) -> dict[str, Any]:
    """Adopt the observed readiness timestamp from the readiness gate, if present."""
    path = (
        Path("docs/forensics/validation/runtime/R6_context_gathering")
        / sha
        / "R6_WORKER_READINESS.json"
    )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("ready") is True:
            return payload
    except Exception:
        pass
    return {}


def _wait_for_worker_snapshot(timeout_s: int = 30) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    last_error = "none"
    while time.time() < deadline:
        try:
            result = celery_app.send_task(
                "app.tasks.r6_resource_governance.runtime_snapshot",
                kwargs={},
                queue="housekeeping",
            )
            return result.get(timeout=10)
        except Exception as exc:  # noqa: BLE001
            last_error = f"{exc.__class__.__name__}:{str(exc)[:160]}"
            time.sleep(1)
    raise RuntimeError(
        "Worker runtime snapshot did not return within timeout "
        f"(timeout_s={timeout_s} last_error={last_error}). "
        "Run scripts/r6/r6_wait_for_worker.py first: elapsed sleep is not "
        "readiness evidence; a task round-trip plus live parent PID is."
    )


def _probe_timeout(ctx: R6Context) -> dict[str, Any]:
    run_id = f"timeout-{uuid4()}"
    start = time.monotonic()
    result = celery_app.send_task(
        "app.tasks.r6_resource_governance.timeout_probe",
        kwargs={"run_id": run_id},
        queue="maintenance",
    )
    error = None
    try:
        result.get(timeout=15)
    except Exception as exc:  # noqa: BLE001
        error = f"{exc.__class__.__name__}:{exc}"
    elapsed_s = time.monotonic() - start

    events = _read_probe_events(ctx.probe_log_path)
    soft_hit = any(
        event.get("event") == "timeout_soft_limit" and event.get("run_id") == run_id
        for event in events
    )
    hard_hit = error is not None and "TimeLimitExceeded" in error
    payload = {
        "run_id": run_id,
        "soft_limit_observed": soft_hit,
        "hard_limit_observed": hard_hit,
        "elapsed_s": elapsed_s,
        "soft_limit_s": 2,
        "hard_limit_s": 4,
        "result_error": error,
    }
    _write_json(
        ctx.output_dir / "R6_PROBE_TIMEOUT.json",
        payload,
        sha=ctx.sha,
        timestamp=ctx.timestamp_utc,
    )
    return payload


def _probe_retry(ctx: R6Context) -> dict[str, Any]:
    run_id = f"retry-{uuid4()}"
    result = celery_app.send_task(
        "app.tasks.r6_resource_governance.retry_probe",
        kwargs={"run_id": run_id},
        queue="housekeeping",
    )
    error = None
    result_state = None
    try:
        result.get(timeout=20)
    except Exception as exc:  # noqa: BLE001
        error = f"{exc.__class__.__name__}:{exc}"
    result_state = result.state

    events = _read_probe_events(ctx.probe_log_path)
    attempt_events = [
        event
        for event in events
        if event.get("event") == "retry_attempt" and event.get("run_id") == run_id
    ]
    attempt_numbers = [
        int(event["attempt"])
        for event in attempt_events
        if isinstance(event.get("attempt"), int)
    ]
    payload = {
        "run_id": run_id,
        "attempt_events": attempt_events,
        "attempt_count": len(attempt_events),
        "attempt_numbers": attempt_numbers,
        "attempt_max": max(attempt_numbers) if attempt_numbers else None,
        "terminal_state": result_state,
        "result_error": error,
    }
    _write_json(
        ctx.output_dir / "R6_PROBE_RETRY.json",
        payload,
        sha=ctx.sha,
        timestamp=ctx.timestamp_utc,
    )
    return payload


def _probe_prefetch(ctx: R6Context) -> dict[str, Any]:
    # Bounded-starvation invariant (NOT an ordering assertion): with
    # concurrency=2, prefetch=1 and max-tasks-per-child=1, four 2 s long tasks
    # on maintenance must not starve four short tasks on housekeeping beyond
    # 20 s. Celery guarantees no exact interleaving; asserting one would
    # measure accidental timing (H-VIII-04). The bound is the guarantee.
    run_id = f"prefetch-{uuid4()}"
    sent_at = datetime.now(timezone.utc)
    published_at_utc = sent_at.isoformat()
    long_ids = [
        celery_app.send_task(
            "app.tasks.r6_resource_governance.prefetch_long_task",
            kwargs={"run_id": run_id, "index": i, "sleep_s": 2.0},
            queue="maintenance",
        ).id
        for i in range(4)
    ]
    short_ids = [
        celery_app.send_task(
            "app.tasks.r6_resource_governance.prefetch_short_task",
            kwargs={"run_id": run_id, "index": i},
            queue="housekeeping",
        ).id
        for i in range(4)
    ]

    result_timeout_s = int(os.getenv(RESULT_GET_TIMEOUT_ENV, "90"))
    long_results = [
        _causal_get(
            ctx, AsyncResult(tid), timeout=result_timeout_s, what=f"prefetch-long-{tid}"
        )
        for tid in long_ids
    ]
    short_results = [
        _causal_get(
            ctx, AsyncResult(tid), timeout=result_timeout_s, what=f"prefetch-short-{tid}"
        )
        for tid in short_ids
    ]

    events = _read_probe_events(ctx.probe_log_path)
    short_start_events = [
        event
        for event in events
        if event.get("event") == "R6_SHORT_TASK_START" and event.get("run_id") == run_id
    ]
    long_start_events = [
        event
        for event in events
        if event.get("event") == "R6_LONG_TASK_START" and event.get("run_id") == run_id
    ]

    short_wait_s = []
    for event in short_start_events:
        ts = event.get("timestamp")
        if isinstance(ts, str):
            started = datetime.fromisoformat(ts)
            short_wait_s.append((started - sent_at).total_seconds())
    max_short_wait_s = max(short_wait_s) if short_wait_s else None
    wait_threshold_s = 20.0
    wait_within_threshold = (
        max_short_wait_s is not None and max_short_wait_s <= wait_threshold_s
    )
    probe_valid = bool(short_start_events)
    payload = {
        "run_id": run_id,
        "tasks_published_at_utc": published_at_utc,
        "result_read_at_utc": _utc_now(),
        "long_result_count": len(long_results),
        "short_start_events": short_start_events,
        "short_start_count": len(short_start_events),
        "long_start_count": len(long_start_events),
        "long_task_count": len(long_ids),
        "short_result_count": len(short_results),
        "max_short_wait_s": max_short_wait_s,
        "short_wait_threshold_s": wait_threshold_s,
        "short_wait_within_threshold": wait_within_threshold,
        "probe_valid": probe_valid,
    }
    _write_json(
        ctx.output_dir / "R6_PROBE_PREFETCH.json",
        payload,
        sha=ctx.sha,
        timestamp=ctx.timestamp_utc,
    )
    return payload


def _probe_recycle(ctx: R6Context) -> dict[str, Any]:
    run_id = f"recycle-{uuid4()}"
    pids = []
    for index in range(3):
        result = celery_app.send_task(
            "app.tasks.r6_resource_governance.pid_probe",
            kwargs={"run_id": run_id, "index": index},
            queue="housekeeping",
        )
        payload = _causal_get(
            ctx, result, timeout=10, what=f"pid-probe-{run_id}-{index}"
        )
        if isinstance(payload, dict) and payload.get("pid"):
            pids.append(int(payload["pid"]))
    unique_pids = sorted(set(pids))
    derived_checks = {
        "assert_unique_pid_count_matches_samples": len(unique_pids) == len(set(pids)),
        "assert_unique_pids_matches_samples": unique_pids == sorted(set(pids)),
    }
    payload = {
        "run_id": run_id,
        "pid_samples": pids,
        "unique_pid_count": len(unique_pids),
        "unique_pids": unique_pids,
        "sample_count": len(pids),
        "recycled_per_task": len(unique_pids) == len(pids) if pids else False,
        "derived_checks": derived_checks,
    }
    _write_json(
        ctx.output_dir / "R6_PROBE_RECYCLE.json",
        payload,
        sha=ctx.sha,
        timestamp=ctx.timestamp_utc,
    )
    return payload


def main() -> int:
    run_url = os.getenv("R6_RUN_URL", "UNKNOWN")
    git_sha = _git_rev_parse_head()
    sha = os.getenv("R6_SHA", git_sha)
    github_sha = os.getenv("GITHUB_SHA")
    if sha != git_sha:
        raise RuntimeError(f"R6_SHA mismatch: env={sha} git={git_sha}")
    if github_sha and github_sha != sha:
        raise RuntimeError(f"R6_SHA mismatch: github={github_sha} env={sha}")
    print(f"R6_SHA={sha}")
    print(f"R6_GIT_SHA={git_sha}")
    if github_sha:
        print(f"R6_GITHUB_SHA={github_sha}")
    timestamp = _utc_now()
    output_root = Path("docs/forensics/validation/runtime/R6_context_gathering")
    output_dir = _ensure_output_dir(output_root, sha)

    worker_log_path = Path(os.getenv(WORKER_LOG_ENV, "r6_worker.log"))
    probe_log_path = Path(os.getenv(PROBE_LOG_ENV, "r6_probe.log"))
    ctx = R6Context(
        sha=sha,
        timestamp_utc=timestamp,
        run_url=run_url,
        output_dir=output_dir,
        worker_log_path=worker_log_path,
        probe_log_path=probe_log_path,
    )
    if probe_log_path.exists():
        probe_log_path.unlink()

    env_snapshot = {
        "R6_SHA": sha,
        "R6_TIMESTAMP_UTC": timestamp,
        "git_status_porcelain": _git_status_porcelain(),
        "run_url": run_url,
        "github_sha": github_sha or "",
        "os": {"platform": platform.platform(), "machine": platform.machine()},
        "python": {"version": sys.version.split()[0], "full": sys.version},
        "celery": {"version": celery_version},
        "container_runtime_version": _run_command(["podman", "--version"]).strip(),
        "postgres_image": os.getenv("R6_POSTGRES_IMAGE", "unknown"),
    }
    _write_json(output_dir / "R6_ENV_SNAPSHOT.json", env_snapshot, sha=sha, timestamp=timestamp)

    # Corrective VIII §11: bind the observed readiness gate into the lifecycle
    # record so a reader can tell never-ready / disappeared / unreachable apart.
    gate = _readiness_evidence(sha)
    parent_pid_at_start = _read_parent_pid()
    lifecycle: dict[str, Any] = {
        "sha": sha,
        "gathering_started_at_utc": timestamp,
        "worker_parent_pid_at_start": parent_pid_at_start,
        "worker_parent_pid_alive_at_start": (
            _pid_alive(parent_pid_at_start) if parent_pid_at_start else False
        ),
        "readiness_gate_observed": bool(gate),
        "worker_ready_timestamp_utc": gate.get("worker_ready_timestamp_utc"),
        "readiness_task_id": (gate.get("task_round_trip") or {}).get("task_id"),
        "broker_scheme": _dsn_scheme_and_hash(
            str(getattr(celery_app.conf, "broker_url", "") or "")
        ).get("scheme"),
        "result_backend_scheme": _dsn_scheme_and_hash(
            str(getattr(celery_app.conf, "result_backend", "") or "")
        ).get("scheme"),
    }
    _write_json(
        output_dir / "R6_WORKER_LIFECYCLE.json",
        lifecycle,
        sha=sha,
        timestamp=timestamp,
    )
    if gate:
        print(
            "R6_READINESS_ADOPTED ready_at="
            f"{gate.get('worker_ready_timestamp_utc')}"
        )
    else:
        print(
            "R6_READINESS_GATE_ABSENT proceeding with inline snapshot polling; "
            "CI must run scripts/r6/r6_wait_for_worker.py first"
        )

    snapshot = _wait_for_worker_snapshot()

    _write_text(
        output_dir / "R6_CELERY_REPORT.log",
        _celery_cli(["report"]),
        sha=sha,
        timestamp=timestamp,
    )
    _write_text(
        output_dir / "R6_CELERY_INSPECT_CONF.log",
        _celery_cli(["inspect", "conf"]),
        sha=sha,
        timestamp=timestamp,
    )
    _write_text(
        output_dir / "R6_CELERY_INSPECT_STATS.log",
        _celery_cli(["inspect", "stats"]),
        sha=sha,
        timestamp=timestamp,
    )
    _write_text(
        output_dir / "R6_ACTIVE_QUEUES.log",
        _celery_cli(["inspect", "active_queues"]),
        sha=sha,
        timestamp=timestamp,
    )
    _write_text(
        output_dir / "R6_TASK_REGISTRY.log",
        _celery_cli(["inspect", "registered"]),
        sha=sha,
        timestamp=timestamp,
    )

    snapshot["sha"] = sha
    snapshot["timestamp_utc"] = timestamp
    snapshot["run_url"] = run_url
    _write_json(output_dir / "R6_CELERY_INSPECT_CONF.json", snapshot, sha=sha, timestamp=timestamp)

    inspector = celery_app.control.inspect(timeout=5)
    stats = inspector.stats() or {}
    active = inspector.active_queues() or {}
    registered = inspector.registered() or {}
    if not active:
        active = {
            "source": "runtime_snapshot_conf",
            "queues": snapshot.get("task_queues", []),
        }

    _write_json(output_dir / "R6_CELERY_INSPECT_STATS.json", stats, sha=sha, timestamp=timestamp)
    _write_json(output_dir / "R6_ACTIVE_QUEUES.json", active, sha=sha, timestamp=timestamp)
    registry_payload = registered
    if not registry_payload:
        registry_payload = {
            "source": "app_registry_fallback",
            "tasks": sorted(celery_app.tasks.keys()),
        }
    _write_json(output_dir / "R6_TASK_REGISTRY.json", registry_payload, sha=sha, timestamp=timestamp)

    matrix_rows = _task_governance_matrix()
    _write_text(
        output_dir / "R6_TASK_GOVERNANCE_MATRIX.md",
        _render_task_matrix_md(matrix_rows),
        sha=sha,
        timestamp=timestamp,
    )

    worker_stats = {}
    if stats:
        _, worker_stats = next(iter(stats.items()))
    concurrency_snapshot = {
        "worker_stats": worker_stats,
        "runtime_snapshot": snapshot,
        "active_queues": active,
    }
    _write_json(
        output_dir / "R6_CONCURRENCY_SNAPSHOT.json",
        concurrency_snapshot,
        sha=sha,
        timestamp=timestamp,
    )

    conf = celery_app.conf
    topology = {
        "task_queues": [q.name for q in (conf.task_queues or [])],
        "task_routes": conf.task_routes or {},
        "task_default_queue": conf.task_default_queue,
        "task_default_exchange": conf.task_default_exchange,
        "task_default_routing_key": conf.task_default_routing_key,
        "active_queues": active,
    }
    _write_json(output_dir / "R6_QUEUE_TOPOLOGY.json", topology, sha=sha, timestamp=timestamp)

    active_list = []
    if isinstance(active, dict) and "queues" in active:
        active_list = active.get("queues") or []
    gap_report = _build_gap_report(snapshot, matrix_rows, active_list)
    _write_text(output_dir / "R6_GAP_REPORT.md", gap_report, sha=sha, timestamp=timestamp)

    # Order matters: the timeout probe intentionally kills a worker process via hard time limits.
    # Run non-destructive probes first to avoid flakiness from post-timeout pool churn.
    _probe_retry(ctx)
    _probe_prefetch(ctx)
    _probe_recycle(ctx)
    _probe_timeout(ctx)

    lifecycle.update(
        {
            "gathering_finished_at_utc": _utc_now(),
            "worker_parent_pid_at_end": _read_parent_pid(),
            "probe_log_event_count": len(_read_probe_events(ctx.probe_log_path)),
        }
    )
    _write_json(
        output_dir / "R6_WORKER_LIFECYCLE.json",
        lifecycle,
        sha=ctx.sha,
        timestamp=ctx.timestamp_utc,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
