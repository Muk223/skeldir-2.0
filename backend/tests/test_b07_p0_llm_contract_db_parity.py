from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/llm_contract_db_parity.py"
CONTRACT = ROOT / "contracts-internal/llm/b07_llm_api_calls_write_contract.json"
FIXTURES = ROOT / "backend/tests/fixtures"


def _run_parity(snapshot: str, shape: str, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(SCRIPT),
            "--contract",
            str(CONTRACT),
            "--shape",
            shape,
            "--mode",
            mode,
            "--schema-snapshot",
            str(FIXTURES / snapshot),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_parity_target_shape_enforce_passes() -> None:
    result = _run_parity("b07_p0_llm_schema_snapshot_current.json", "target_row_shape", "enforce")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "status: PASS" in result.stdout


def test_parity_enforce_fails_missing_column() -> None:
    result = _run_parity("b07_p0_llm_schema_snapshot_missing_column.json", "target_row_shape", "enforce")
    assert result.returncode == 1
    assert "missing columns" in result.stdout
    assert "model" in result.stdout


def test_parity_enforce_fails_type_mismatch() -> None:
    result = _run_parity("b07_p0_llm_schema_snapshot_wrong_type.json", "target_row_shape", "enforce")
    assert result.returncode == 1
    assert "type mismatches" in result.stdout
    assert "cost_cents" in result.stdout


def test_parity_target_shape_report_emits_mismatch() -> None:
    result = _run_parity("b07_p0_llm_schema_snapshot_current.json", "target_row_shape", "report")
    assert result.returncode == 0
    assert "status: PASS" in result.stdout
