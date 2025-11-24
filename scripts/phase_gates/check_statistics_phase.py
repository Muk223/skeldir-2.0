#!/usr/bin/env python3
"""
Statistics phase gate.

Confirms Bayesian sampling evidence meets R-hat / ESS thresholds and exited
successfully.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from utils import fail, load_json, ok, parse_args  # noqa: E402


def main() -> None:
    args = parse_args()
    root: Path = args.root

    sampling_path = root / "statistics" / "sampling_output.json"
    if not sampling_path.is_file():
        sampling_path = root / "statistics" / "model_results.json"
    if not sampling_path.is_file():
        fail("No sampling_output.json or model_results.json found")

    data = load_json(sampling_path)
    try:
        sampling = data["sampling_tests"]["pymc_sampling"]
        slope_rhat = float(sampling["slope_rhat"])
        intercept_rhat = float(sampling["intercept_rhat"])
        slope_ess = float(sampling["slope_ess"])
        intercept_ess = float(sampling["intercept_ess"])
        exit_code = int(data.get("exit_code", 1))
    except Exception as exc:
        fail(f"Sampling JSON missing expected fields: {exc}")

    if exit_code != 0:
        fail(f"Sampling exit_code != 0 (value: {exit_code})")
    if not (slope_rhat < 1.01 and intercept_rhat < 1.01):
        fail(
            f"R-hat thresholds not met: slope={slope_rhat}, intercept={intercept_rhat}"
        )
    if not (slope_ess > 400 and intercept_ess > 400):
        fail(f"ESS thresholds not met: slope={slope_ess}, intercept={intercept_ess}")

    ok(f"Sampling evidence satisfies thresholds ({sampling_path})")
    ok("Statistics phase gate: PASS")


if __name__ == "__main__":
    main()
