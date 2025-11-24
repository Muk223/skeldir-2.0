#!/usr/bin/env python3
"""
Runtime phase gate.

Validates that the runtime evidence shows both structural readiness (Tier A)
and empirical multi-process operation (Tier B).
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from utils import fail, latest_with_prefix, ok, parse_args, require_files  # noqa: E402

EXPECTED_PROCESSES = ("uvicorn", "celery", "redis", "postgres")
EXPECTED_PORTS = (":8000", ":6379", ":5432")


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    args = parse_args()
    root: Path = args.root
    runtime_dir = root / "runtime"

    # Tier A: static configuration check log
    config_log = latest_with_prefix(root, "runtime", "runtime_config_static_check")
    config_text = _load_text(config_log)
    if "FAIL" in config_text.upper():
        fail(f"Static runtime config log reports failure: {config_log}")
    ok(f"Static runtime configuration validated via {config_log}")

    # Tier B: process and port evidence
    process_snapshot = runtime_dir / "process_snapshot.txt"
    open_ports = runtime_dir / "open_ports.txt"
    auto_restart = latest_with_prefix(root, "runtime", "auto_restart_log")
    require_files([process_snapshot, open_ports, auto_restart])

    ps_text = _load_text(process_snapshot)
    for proc in EXPECTED_PROCESSES:
        if proc not in ps_text:
            fail(f"Process '{proc}' not observed in {process_snapshot}")
    ok("All expected runtime processes present in process_snapshot.txt")

    ports_text = _load_text(open_ports)
    for port in EXPECTED_PORTS:
        if port not in ports_text:
            fail(f"Port {port} not found in {open_ports}")
    ok("All expected service ports observed in open_ports.txt")

    restart_text = _load_text(auto_restart).upper()
    if "CRASH" not in restart_text or "RESTART" not in restart_text:
        fail(f"Auto-restart log {auto_restart} must show crash and restart markers")
    ok(f"Auto-restart behavior proven via {auto_restart}")

    ok("Runtime phase gate: PASS")


if __name__ == "__main__":
    main()
