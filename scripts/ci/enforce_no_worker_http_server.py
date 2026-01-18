#!/usr/bin/env python3
"""
B0.5.6.1 Guardrail: Fail-closed enforcement against worker-side HTTP server primitives.

This script prevents reintroduction of worker HTTP sidecar drift by detecting:
1. Imports of stdlib server modules (wsgiref.simple_server, http.server, socketserver)
2. Imports of prometheus_client.exposition.start_http_server
3. Server loop patterns (serve_forever, make_server)

Rationale:
- Phase 5 requires hermetic workers without network surfaces.
- The existing hermeticity scanner only checks direct 'socket' imports, missing transitive
  usage via stdlib server modules (wsgiref → http.server → socketserver → socket).
- This guardrail closes that enforcement gap.

Exit codes:
- 0: No forbidden patterns found
- 1: Forbidden patterns detected (CI should fail)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate worker-side HTTP server drift
FORBIDDEN_IMPORT_PATTERNS = [
    r"^\s*from\s+wsgiref\.simple_server\s+import",
    r"^\s*from\s+wsgiref\s+import\s+simple_server",
    r"^\s*import\s+wsgiref\.simple_server",
    r"^\s*from\s+http\.server\s+import",
    r"^\s*import\s+http\.server",
    r"^\s*from\s+socketserver\s+import",
    r"^\s*import\s+socketserver",
    r"^\s*from\s+prometheus_client\.exposition\s+import.*start_http_server",
    r"^\s*from\s+prometheus_client\s+import.*start_http_server",
]

FORBIDDEN_CALL_PATTERNS = [
    r"\.serve_forever\s*\(",
    r"\bmake_server\s*\(",
    r"\bstart_http_server\s*\(",
    r"\bHTTPServer\s*\(",
    r"\bWSGIServer\s*\(",
    r"\bTCPServer\s*\(",
]

# Allowlist: paths that are permitted to contain these patterns (e.g., this script itself, tests)
ALLOWLIST_PATH_PATTERNS = [
    r"scripts/ci/enforce_no_worker_http_server\.py$",  # This script
    r"backend/app/observability/worker_metrics_exporter\.py$",  # Dedicated exporter (not in worker runtime)
    r"backend/tests/",  # Test files may mock or test detection
    r"tests/",  # Test files
    r"__pycache__/",  # Bytecode
    r"\.venv",  # Virtual environments
    r"venv/",  # Virtual environments
    r"site-packages/",  # Installed packages
    r"node_modules/",  # Node modules
]


def repo_root() -> Path:
    """Return the repository root (parent of scripts/ci/)."""
    return Path(__file__).resolve().parents[2]


def is_allowlisted(path: Path) -> bool:
    """Check if a path is in the allowlist."""
    rel_path = str(path.relative_to(repo_root())).replace("\\", "/")
    for pattern in ALLOWLIST_PATH_PATTERNS:
        if re.search(pattern, rel_path):
            return True
    return False


def scan_file(path: Path) -> List[Tuple[int, str, str]]:
    """
    Scan a single Python file for forbidden patterns.

    Returns list of (line_number, pattern_type, matched_line).
    """
    violations: List[Tuple[int, str, str]] = []

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return violations

    lines = content.splitlines()

    for lineno, line in enumerate(lines, start=1):
        # Check import patterns
        for pattern in FORBIDDEN_IMPORT_PATTERNS:
            if re.search(pattern, line):
                violations.append((lineno, "import", line.strip()))
                break  # One violation per line is enough

        # Check call patterns
        for pattern in FORBIDDEN_CALL_PATTERNS:
            if re.search(pattern, line):
                violations.append((lineno, "call", line.strip()))
                break

    return violations


def scan_directory(root: Path) -> List[Tuple[Path, int, str, str]]:
    """
    Recursively scan a directory for Python files with forbidden patterns.

    Returns list of (file_path, line_number, pattern_type, matched_line).
    """
    all_violations: List[Tuple[Path, int, str, str]] = []

    for py_file in root.rglob("*.py"):
        if is_allowlisted(py_file):
            continue

        file_violations = scan_file(py_file)
        for lineno, ptype, line in file_violations:
            all_violations.append((py_file, lineno, ptype, line))

    return all_violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="B0.5.6.1 Guardrail: Detect worker HTTP server primitives"
    )
    parser.add_argument(
        "--output",
        help="Optional output file path for violation report",
    )
    parser.add_argument(
        "--scan-path",
        default="backend/app",
        help="Path to scan (relative to repo root, default: backend/app)",
    )
    args = parser.parse_args()

    root = repo_root()
    scan_root = root / args.scan_path

    if not scan_root.exists():
        print(f"ERROR: Scan path does not exist: {scan_root}", file=sys.stderr)
        return 1

    violations = scan_directory(scan_root)

    # Build report
    report_lines = [
        "B0.5.6.1 Worker HTTP Server Guardrail Scan",
        f"Scanned: {scan_root}",
        f"Violations: {len(violations)}",
        "",
    ]

    if violations:
        report_lines.append("VIOLATIONS DETECTED:")
        for path, lineno, ptype, line in violations:
            rel_path = path.relative_to(root)
            report_lines.append(f"  {rel_path}:{lineno} [{ptype}] {line}")
        report_lines.append("")
        report_lines.append(
            "FAIL: Worker HTTP server primitives detected. "
            "Remove these imports/calls to pass B0.5.6.1 guardrail."
        )
    else:
        report_lines.append("PASS: No worker HTTP server primitives detected.")

    report = "\n".join(report_lines)

    # Output
    print(report)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report + "\n", encoding="utf-8")

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
