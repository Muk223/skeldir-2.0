#!/usr/bin/env python3
"""
Phase gate dispatcher.

Dispatches to dedicated gate runners once they are implemented.
"""

from __future__ import annotations

# Bootstrap sys.path FIRST (inline to avoid circular import)
import sys
from pathlib import Path as _Path
_repo_root = _Path(__file__).resolve().parents[2]
_backend_root = _repo_root / "backend"
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))
del _Path, _repo_root, _backend_root

import argparse
# sys already imported above for bootstrap
from importlib import import_module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute a phase gate.")
    parser.add_argument("phase", help="Phase identifier (e.g., B0.1)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    phase = args.phase.upper()

    handlers = {
        "B0.1": "scripts.phase_gates.b0_1_gate",
        "B0.2": "scripts.phase_gates.b0_2_gate",
        "B0.3": "scripts.phase_gates.b0_3_gate",
        "B0.4": "scripts.phase_gates.b0_4_gate",
        "SCHEMA_GUARD": "scripts.phase_gates.schema_guard_gate",
    }

    if phase not in handlers:
        print(f"Unknown phase '{phase}'.", file=sys.stderr)
        return 2

    module = import_module(handlers[phase])
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
