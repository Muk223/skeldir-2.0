"""R6 worker readiness gate (Corrective VIII).

Event-based transition condition for the R6 proof plane. The harness must
proceed only after the actual prerequisite is physically observed::

    elapsed time != readiness evidence

Polls with a deadline until a task round-trip through the real
broker/result-backend topology succeeds. Remote-control ``ping`` is recorded
as telemetry only: the PostgreSQL-backed Celery transport does not
contractually guarantee broadcast-inspect visibility, so readiness must never
be gated on ``ping`` alone (H-VIII-03). The authoritative signal is a
published task whose result is durably readable, plus a live worker parent
PID.

On success writes ``R6_WORKER_READINESS.json`` into the SHA-anchored R6
output directory and exits 0. On deadline exits 1 after writing the same
file with a causally discriminating ``failure_cause`` (never ``TimeoutError``
alone)::

    WORKER_NEVER_READY | WORKER_DISAPPEARED | CONTROL_CHANNEL_UNREACHABLE
    | BROKER_UNREACHABLE | RESULT_BACKEND_UNREACHABLE | SNAPSHOT_TASK_FAILED

Usage::

    python scripts/r6/r6_wait_for_worker.py

Environment::

    R6_SHA / GITHUB_SHA   candidate identity (must agree when both present)
    R6_WORKER_PIDFILE     worker pidfile (default /tmp/r6_worker.pid)
    R6_READINESS_DEADLINE_S  total budget (default 120)
    R6_READINESS_POLL_S      poll interval (default 2)
    CELERY_BROKER_URL / CELERY_RESULT_BACKEND  real topology under test
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


PIDFILE_ENV = "R6_WORKER_PIDFILE"
DEADLINE_ENV = "R6_READINESS_DEADLINE_S"
POLL_ENV = "R6_READINESS_POLL_S"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candidate_sha() -> str:
    sha = os.getenv("R6_SHA") or os.getenv("GITHUB_SHA") or ""
    if not sha:
        try:
            sha = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT
                )
                .decode("utf-8", errors="replace")
                .strip()
            )
        except Exception:
            sha = "UNKNOWN"
    github_sha = os.getenv("GITHUB_SHA") or ""
    if github_sha and sha and github_sha != sha and sha != "UNKNOWN":
        raise SystemExit(
            f"R6_READINESS_SHA_MISMATCH env={sha} github={github_sha}"
        )
    return sha or github_sha or "UNKNOWN"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True


def _read_parent_pid(pidfile: Path) -> int | None:
    try:
        text = pidfile.read_text(encoding="utf-8").strip().split()[0]
        return int(text)
    except Exception:
        return None


def _sync_dsn(raw: str) -> str:
    """Coerce a Celery broker/result URL to a plain SQLAlchemy DSN."""
    cleaned = (raw or "").strip()
    for prefix in ("sqla+postgresql://", "db+postgresql://"):
        if cleaned.startswith(prefix):
            return "postgresql://" + cleaned[len(prefix):]
    return cleaned


def _tcp_or_sql_reachable(dsn: str, timeout_s: float = 5.0) -> tuple[bool, str]:
    if not dsn:
        return False, "empty-dsn"
    if not dsn.startswith("postgresql"):
        return False, f"non-postgres-scheme:{urlsplit(dsn).scheme}"
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(
            _sync_dsn(dsn), connect_args={"connect_timeout": int(timeout_s)}
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True, "select-1-ok"
    except Exception as exc:  # noqa: BLE001
        return False, f"{exc.__class__.__name__}:{str(exc)[:200]}"


def main() -> int:
    started_monotonic = time.monotonic()
    started_utc = _utc_now()
    sha = _candidate_sha()
    pidfile = Path(os.getenv(PIDFILE_ENV, "/tmp/r6_worker.pid"))
    try:
        deadline_s = float(os.getenv(DEADLINE_ENV, "120"))
    except ValueError:
        deadline_s = 120.0
    try:
        poll_s = float(os.getenv(POLL_ENV, "2"))
    except ValueError:
        poll_s = 2.0

    output_dir = Path("docs/forensics/validation/runtime/R6_context_gathering") / sha
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "R6_WORKER_READINESS.json"

    broker_url = ""
    backend_url = ""
    try:
        from app.celery_app import celery_app  # noqa: E402
    except Exception as exc:  # noqa: BLE001
        failure_evidence: dict = {
            "R6_SHA": sha,
            "R6_TIMESTAMP_UTC": started_utc,
            "pidfile": str(pidfile),
            "ready": False,
            "failure_cause": f"IMPORT_FAIL:{exc.__class__.__name__}:{str(exc)[:200]}",
            "attempts": [],
            "elapsed_s": time.monotonic() - started_monotonic,
        }
        out_path.write_text(
            json.dumps(failure_evidence, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(f"R6_READINESS_IMPORT_FAIL {exc.__class__.__name__}:{exc}")
        return 1

    broker_url = str(getattr(celery_app.conf, "broker_url", "") or "")
    backend_url = str(getattr(celery_app.conf, "result_backend", "") or "")

    evidence: dict = {
        "R6_SHA": sha,
        "R6_TIMESTAMP_UTC": started_utc,
        "pidfile": str(pidfile),
        "deadline_s": deadline_s,
        "poll_s": poll_s,
        "attempts": [],
        "ping_ever_succeeded": False,
        "round_trip_ever_succeeded": False,
        "parent_pid_ever_alive": False,
        "parent_pid_last_seen_dead": False,
    }

    deadline = time.monotonic() + deadline_s
    attempt = 0
    ever_ping = False
    ever_round_trip = False
    ever_pid_alive = False
    saw_ping_then_lost = False
    while time.monotonic() < deadline:
        attempt += 1
        loop: dict = {"attempt": attempt, "at_utc": _utc_now()}
        parent_pid = _read_parent_pid(pidfile)
        loop["parent_pid"] = parent_pid
        pid_alive = _pid_alive(parent_pid) if parent_pid else False
        loop["parent_pid_alive"] = pid_alive
        if pid_alive:
            ever_pid_alive = True
        elif ever_round_trip or ever_ping:
            saw_ping_then_lost = True

        broker_ok, broker_detail = _tcp_or_sql_reachable(broker_url)
        backend_ok, backend_detail = _tcp_or_sql_reachable(backend_url)
        loop["broker_reachable"] = broker_ok
        loop["broker_detail"] = broker_detail
        loop["result_backend_reachable"] = backend_ok
        loop["result_backend_detail"] = backend_detail

        ping_ok = False
        ping_detail = ""
        try:
            inspector = celery_app.control.inspect(timeout=5)
            ping = inspector.ping() or {}
            ping_ok = bool(ping)
            ping_detail = f"replied={len(ping)}"
            if ping_ok:
                ever_ping = True
        except Exception as exc:  # noqa: BLE001
            ping_detail = f"{exc.__class__.__name__}:{str(exc)[:160]}"
            if ever_ping:
                saw_ping_then_lost = True
        loop["ping_succeeds"] = ping_ok
        loop["ping_detail"] = ping_detail

        round_trip_ok = False
        round_trip_detail = ""
        published_at = _utc_now()
        loop["task_published_at_utc"] = published_at
        try:
            result = celery_app.send_task(
                "app.tasks.r6_resource_governance.runtime_snapshot",
                kwargs={},
                queue="housekeeping",
            )
            loop["task_id"] = result.id
            payload = result.get(timeout=15)
            read_at = _utc_now()
            loop["result_read_at_utc"] = read_at
            if isinstance(payload, dict) and payload.get("worker_pid"):
                round_trip_ok = True
                ever_round_trip = True
                loop["worker_pid"] = payload.get("worker_pid")
                loop["worker_hostname"] = payload.get("hostname")
                round_trip_detail = f"worker_pid={payload.get('worker_pid')}"
            else:
                round_trip_detail = "snapshot-missing-worker-pid"
        except Exception as exc:  # noqa: BLE001
            round_trip_detail = f"{exc.__class__.__name__}:{str(exc)[:200]}"
        loop["round_trip_ok"] = round_trip_ok
        loop["round_trip_detail"] = round_trip_detail
        evidence["attempts"].append(loop)

        print(
            f"R6_READINESS attempt={attempt} pid_alive={pid_alive} "
            f"broker={broker_ok} backend={backend_ok} ping={ping_ok} "
            f"round_trip={round_trip_ok} detail={round_trip_detail or ping_detail}"
        )
        if round_trip_ok and pid_alive:
            evidence.update(
                {
                    "ready": True,
                    "worker_ready_timestamp_utc": _utc_now(),
                    "worker_parent_pid": parent_pid,
                    "worker_parent_pid_alive": True,
                    "broker_reachable": True,
                    "result_backend_reachable": True,
                    "remote_control_ping_succeeds": ping_ok,
                    "task_round_trip": {
                        "published_at_utc": published_at,
                        "result_read_at_utc": loop.get("result_read_at_utc"),
                        "task_id": loop.get("task_id"),
                        "worker_pid": loop.get("worker_pid"),
                    },
                    "ping_ever_succeeded": ever_ping,
                    "round_trip_ever_succeeded": True,
                    "parent_pid_ever_alive": True,
                    "elapsed_s": time.monotonic() - started_monotonic,
                }
            )
            out_path.write_text(
                json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8"
            )
            print(
                f"R6_WORKER_READY sha={sha} attempts={attempt} "
                f"elapsed_s={evidence['elapsed_s']:.1f}"
            )
            return 0

        time.sleep(poll_s)

    if not broker_ok:
        cause = "BROKER_UNREACHABLE"
    elif not backend_ok:
        cause = "RESULT_BACKEND_UNREACHABLE"
    elif saw_ping_then_lost or (ever_round_trip and not pid_alive):
        cause = "WORKER_DISAPPEARED"
    elif ever_ping and not ever_round_trip:
        cause = "CONTROL_CHANNEL_UNREACHABLE"
    elif not ever_pid_alive and not ever_round_trip:
        cause = "WORKER_NEVER_READY"
    else:
        cause = "SNAPSHOT_TASK_FAILED"
    evidence.update(
        {
            "ready": False,
            "failure_cause": cause,
            "ping_ever_succeeded": ever_ping,
            "round_trip_ever_succeeded": ever_round_trip,
            "parent_pid_ever_alive": ever_pid_alive,
            "parent_pid_last_seen_dead": not pid_alive,
            "elapsed_s": time.monotonic() - started_monotonic,
        }
    )
    out_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(f"R6_WORKER_NOT_READY sha={sha} failure_cause={cause} attempts={attempt}")
    print(f"R6_WORKER_READINESS_EVIDENCE={out_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
