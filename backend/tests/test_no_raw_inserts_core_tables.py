"""
Static guard that forbids raw inserts into core tables outside explicit allowlists.

Any INSERT INTO <core_table> must either:
- Live in a file listed in ALLOWLIST_PATHS with justification, or
- Be preceded by a marker comment containing 'RAW_SQL_ALLOWLIST'.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from backend.tests.builders.manifest import CORE_TABLE_BUILDERS

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = REPO_ROOT / "backend" / "tests"

# File-level allowlist for legacy contract/rls tests pending refactor.
ALLOWLIST_PATHS: Dict[str, str] = {
    "backend/tests/conftest.py": "Legacy tenant bootstrap helper during migration",
    "backend/tests/test_b047_observability.py": "Legacy observability webhook seed",
    "backend/tests/test_b047_logging_and_metrics_contract.py": "Legacy logging/metrics contract seed",
    "backend/tests/test_b045_webhooks.py": "Legacy webhook contract seed",
    "backend/tests/test_b046_integration.py": "Legacy integration webhook seed",
    "backend/tests/test_b0532_window_idempotency.py": "Legacy idempotency fixture seed",
    "backend/tests/test_b0533_revenue_input_contract.py": "Legacy revenue input contract seed",
    "backend/tests/test_b0534_worker_tenant_isolation.py": "Legacy worker isolation seed",
    "backend/tests/test_b0535_worker_readonly_ingestion.py": "Legacy worker read-only guard patterns",
    "backend/tests/test_b0536_attribution_e2e.py": "Legacy E2E attribution seed",
    "backend/tests/test_gate4_rls_celery.py": "Legacy Celery RLS contract seed",
    "backend/tests/test_gate4_rls_minimal.py": "Legacy minimal RLS contract seed",
    "backend/tests/test_rls_e2e.py": "Template RLS test plan (comments only)",
    "backend/tests/integration/test_pii_guardrails.py": "PII guardrail trigger assertions",
    "backend/tests/integration/test_data_retention.py": "Retention integration seed fixtures",
}


def _has_allowlist_marker(lines: List[str], idx: int) -> bool:
    """Check nearby lines for RAW_SQL_ALLOWLIST marker to account for multiline SQL strings."""
    if "RAW_SQL_ALLOWLIST" in lines[idx]:
        return True
    for offset in range(1, 6):
        if idx - offset >= 0 and "RAW_SQL_ALLOWLIST" in lines[idx - offset]:
            return True
    return False


def test_no_raw_inserts_into_core_tables():
    tables_pattern = "|".join(CORE_TABLE_BUILDERS.keys())
    pattern = re.compile(rf"INSERT\s+INTO\s+({tables_pattern})\b", re.IGNORECASE)
    failures: List[str] = []

    for path in TEST_ROOT.rglob("*.py"):
        rel_path = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines):
            for match in pattern.finditer(line):
                table = match.group(1)
                allowed = rel_path in ALLOWLIST_PATHS or _has_allowlist_marker(
                    lines, idx
                )
                if not allowed:
                    failures.append(
                        f"{rel_path}:{idx+1} raw INSERT INTO {table} without RAW_SQL_ALLOWLIST marker"
                    )
    if failures:
        allowlist_help = "\n".join(
            f"- {path}: {reason}" for path, reason in ALLOWLIST_PATHS.items()
        )
        message = "Disallowed raw inserts detected:\n" + "\n".join(failures)
        if ALLOWLIST_PATHS:
            message += "\nAllowed locations:\n" + allowlist_help
        raise AssertionError(message)
