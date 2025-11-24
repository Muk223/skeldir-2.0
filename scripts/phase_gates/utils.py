"""
Shared helpers for empirical phase gate scripts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable


def parse_args(default_root: str = "evidence_registry") -> argparse.Namespace:
    """Parse CLI args, allowing callers to override the evidence root."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(default_root),
        help="Evidence registry root (default: evidence_registry/)",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    """Print a failure message and exit with error code 1."""
    print(f"[FAIL] {message}")
    sys.exit(1)


def ok(message: str) -> None:
    """Print a success message."""
    print(f"[OK] {message}")


def require_files(paths: Iterable[Path]) -> None:
    """Ensure all files exist, failing with a helpful message if not."""
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        fail(f"Required artifact(s) missing: {', '.join(missing)}")


def load_json(path: Path) -> dict:
    """Load JSON from a file with UTF-8 decoding."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        fail(f"Failed to parse JSON {path}: {exc}")
        raise


def latest_with_prefix(root: Path, subdir: str, prefix: str) -> Path:
    """
    Locate the lexicographically latest file in root/subdir with the prefix.
    """
    directory = root / subdir
    if not directory.is_dir():
        fail(f"Evidence subdirectory missing: {directory}")
    matches = sorted(directory.glob(f"{prefix}_*"))
    if not matches:
        fail(f"No artifact matching pattern {subdir}/{prefix}_*")
    return matches[-1]
