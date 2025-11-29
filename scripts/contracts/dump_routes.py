#!/usr/bin/env python3
"""
B0.1 Stub: Route Graph Generator
Placeholder for implementation route introspection.
Full route discovery and graph construction deferred to B0.2 enforcement phase.
"""

import json
from pathlib import Path
import sys


def main() -> int:
    """Write an empty R-graph placeholder so CI can progress."""
    output_dir = Path("tmp")
    output_dir.mkdir(exist_ok=True)

    r_graph_path = output_dir / "r_graph.json"
    r_graph = {
        "version": "1.0.0",
        "source": "implementation",
        "routes": [],
        "metadata": {
            "stub": True,
            "phase": "B0.1",
            "note": "Full route introspection deferred to B0.2"
        }
    }

    with r_graph_path.open("w", encoding="utf-8") as fh:
        json.dump(r_graph, fh, indent=2)

    print(f"[dump_routes] B0.1 stub wrote placeholder to {r_graph_path}")
    print("[dump_routes] Routes discovered: 0 (stub mode)")
    print("[dump_routes] Full implementation deferred to B0.2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
