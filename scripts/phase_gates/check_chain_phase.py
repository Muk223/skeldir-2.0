#!/usr/bin/env python3
"""
Global evidence chain gate.

Ensures the empirical chain document shows each phase marked PASS with no
outstanding gaps.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from utils import fail, ok, parse_args  # noqa: E402

REQUIRED_MARKERS = [
    "Runtime phase gate: PASS",
    "Contract phase gate: PASS",
    "Statistics phase gate: PASS",
    "Privacy phase gate: PASS",
]
FORBIDDEN_TOKENS = ("DEFERRED", "FAILED", "MISSING")


def main() -> None:
    args = parse_args()
    root: Path = args.root
    chain_path = root / "EMPIRICAL_CHAIN.md"
    if not chain_path.is_file():
        fail("EMPIRICAL_CHAIN.md missing from evidence registry")

    text = chain_path.read_text(encoding="utf-8")
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            fail(f"Chain document missing '{marker}'")

    upper = text.upper()
    for token in FORBIDDEN_TOKENS:
        if token in upper:
            fail(f"Chain document still contains '{token}' markers")

    ok("Evidence chain document lists all phases as PASS with no outstanding gaps")
    ok("Chain phase gate: PASS")


if __name__ == "__main__":
    main()
