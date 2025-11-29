#!/usr/bin/env python3
"""
B0.1 Stub: Static Contract Conformance Checker
Placeholder for route-operation graph comparison.
Full conformance validation deferred to B0.2 enforcement phase.
"""

import json
from pathlib import Path
import sys


def load_graph(path: Path, name: str) -> dict:
    """Load a JSON graph file if it exists."""
    if not path.exists():
        print(f"[conformance] ERROR: {name} graph not found at {path}", file=sys.stderr)
        sys.exit(1)

    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    """Perform minimal conformance check on stub graphs."""
    r_graph = load_graph(Path("tmp/r_graph.json"), "R")
    c_graph = load_graph(Path("tmp/c_graph.json"), "C")

    print("[conformance] B0.1 stub: minimal graph validation")
    print(f"[conformance] R-graph routes: {len(r_graph.get('routes', []))}")
    print(f"[conformance] C-graph operations: {len(c_graph.get('operations', []))}")

    if r_graph.get("metadata", {}).get("stub") and c_graph.get("metadata", {}).get("stub"):
        print("[conformance] PASS: Stub graphs detected; full comparison deferred to B0.2")
        return 0

    print("[conformance] WARN: Non-stub graphs detected; enforcement deferred to B0.2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
