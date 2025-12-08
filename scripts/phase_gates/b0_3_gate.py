#!/usr/bin/env python3
"""
B0.3 gate runner for database schema foundation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "backend" / "validation" / "evidence" / "database"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def resolve_bash_executable() -> str:
    """Locate a usable bash executable across platforms."""
    candidate_env = [
        os.environ.get("B0X_BASH"),
        os.environ.get("GIT_BASH"),
        os.environ.get("BASH"),
    ]
    candidate_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ]
    for candidate in candidate_env:
        if candidate and (Path(candidate).exists() or shutil.which(candidate)):
            return candidate
    for candidate in candidate_paths:
        if Path(candidate).exists():
            return candidate
    resolved = shutil.which("bash")
    return resolved or "bash"


BASH_EXE = resolve_bash_executable()


class GateFailure(RuntimeError):
    pass


def run_command(cmd: List[str], log_name: str, env: dict | None = None) -> None:
    log_path = EVIDENCE_DIR / log_name
    with open(log_path, "w", encoding="utf-8") as log_file:
        process = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
    if process.returncode != 0:
        raise GateFailure(f"Command {' '.join(cmd)} failed (see {log_path})")


def run_b0_3_gate() -> dict:
    summary = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "steps": [],
    }
    env = os.environ.copy()
    if "DATABASE_URL" not in env:
        raise GateFailure("DATABASE_URL environment variable is required.")

    # R1: Schema validation via Alembic + compliance script
    run_command(["alembic", "upgrade", "heads"], "alembic_upgrade_head.log", env=env)
    run_command(
        [
            "python",
            "scripts/validate-schema-compliance.py",
            "--output",
            str(EVIDENCE_DIR / "schema_validation_report.json"),
        ],
        "schema_validation.log",
        env=env,
    )
    summary["steps"].append({"name": "schema_validation", "status": "success"})

    # R2: Migration downgrade/upgrade cycle
    run_command(["alembic", "downgrade", "-1"], "alembic_downgrade.log", env=env)
    run_command(["alembic", "upgrade", "heads"], "alembic_upgrade_after_downgrade.log", env=env)
    summary["steps"].append({"name": "migration_cycle", "status": "success"})

    # R3: Guardrails and idempotency tests
    run_command(
        [BASH_EXE, "scripts/database/test-data-integrity.sh"],
        "test_data_integrity.log",
        env=env,
    )
    run_command(
        [BASH_EXE, "scripts/database/validate-pii-guardrails.sh"],
        "validate_pii_guardrails.log",
        env=env,
    )
    run_command(
        [BASH_EXE, "scripts/database/run-audit-scan.sh"],
        "run_audit_scan.log",
        env=env,
    )
    summary["steps"].append({"name": "guardrails", "status": "success"})

    # R4: Query performance evidence
    run_command(
        [
            "python",
            "scripts/database/run_query_performance.py",
            "--output",
            str(EVIDENCE_DIR / "query_performance_report.json"),
        ],
        "query_performance.log",
        env=env,
    )
    summary["steps"].append({"name": "query_performance", "status": "success"})

    return summary


def main() -> int:
    summary_path = EVIDENCE_DIR / "b0_3_summary.json"
    ack_path = REPO_ROOT / "backend" / "validation" / "evidence" / "phase_ack" / "B0_3.json"
    try:
        summary = run_b0_3_gate()
        summary["status"] = "success"
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        ack_path.parent.mkdir(parents=True, exist_ok=True)
        ack_payload = {
            "phase": "B0.3",
            "status": "PASS",
            "timestamp": summary["timestamp"],
            "steps": summary["steps"],
        }
        with open(ack_path, "w", encoding="utf-8") as ack_file:
            json.dump(ack_payload, ack_file, indent=2)
        print("B0.3 gate completed successfully.")
        return 0
    except GateFailure as exc:
        summary = {
            "status": "failure",
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "error": str(exc),
        }
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        print(f"B0.3 gate failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
