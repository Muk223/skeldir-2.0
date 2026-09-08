"""Corrective VIII falsifier B: required-execution identity sensor.

Asserts the R6 required context is emitted from exactly one governance
lifecycle family (merge_group + pull_request) and never from the post-merge
soak lifecycle (push). Reintroducing a push emission of the required name
turns this test RED; exact restore returns GREEN.

This test shells to the governing sensor
``scripts/ci/validate_b25_p14_viii_execution_identity.py`` so the pytest
surface and the R6 workflow step adjudicate the identical rule.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SENSOR = REPO_ROOT / "scripts" / "ci" / "validate_b25_p14_viii_execution_identity.py"


def test_viii_required_execution_identity_single_lifecycle() -> None:
    proc = subprocess.run(
        [sys.executable, str(SENSOR)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        "R6 required-execution identity violated:\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "R6_EXECUTION_IDENTITY_PASS" in proc.stdout
