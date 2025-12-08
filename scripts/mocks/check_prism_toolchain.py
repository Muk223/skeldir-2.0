#!/usr/bin/env python3
"""
Ensure Prism CLI and Node toolchain are available.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Prism toolchain.")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the JSON report.",
    )
    return parser.parse_args()


def build_prism_command() -> list[str]:
    base_cmd = ["npx", "@stoplight/prism-cli", "--version"]
    if os.name == "nt":
        return ["cmd", "/c", *base_cmd]
    return base_cmd


def get_prism_version() -> str:
    process = subprocess.run(
        build_prism_command(),
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr or process.stdout or "Prism CLI error.")
    return process.stdout.strip().splitlines()[0]


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        version = get_prism_version()
        report = {"status": "success", "version": version}
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Prism CLI available: {version}")
        return 0
    except Exception as exc:
        report = {"status": "failure", "error": str(exc)}
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"Prism CLI check failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
