#!/usr/bin/env python3
"""
Validate mock server configuration against the registry and Procfile.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate mock configuration.")
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the JSON report.",
    )
    return parser.parse_args()


def load_registry(repo_root: Path) -> dict:
    registry_path = repo_root / "scripts" / "contracts" / "mock_registry.json"
    with open(registry_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def parse_procfile(repo_root: Path) -> dict[str, dict]:
    procfile_path = repo_root / "Procfile"
    mocks: dict[str, dict] = {}
    pattern = re.compile(r"-p\s+(\d+)")
    with open(procfile_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if not line.startswith("mock_"):
                continue
            name, _, command = line.partition(":")
            match = pattern.search(command)
            port = int(match.group(1)) if match else None
            mocks[name.replace("mock_", "")] = {
                "port": port,
                "command": command.strip(),
            }
    return mocks


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    registry = load_registry(repo_root)
    procfile_mocks = parse_procfile(repo_root)

    issues: list[str] = []
    bundles_root = repo_root / "api-contracts" / "dist" / "openapi" / "v1"

    for mock in registry.get("primary_mocks", []):
        if mock not in procfile_mocks:
            issues.append(f"Mock '{mock}' missing from Procfile.")
            continue
        info = procfile_mocks[mock]
        expected_port = registry["port_mapping"].get(mock)
        if info["port"] != expected_port:
            issues.append(
                f"Mock '{mock}' port mismatch: registry {expected_port}, Procfile {info['port']}"
            )
        if "api-contracts/dist/openapi/v1" not in info["command"]:
            issues.append(
                f"Mock '{mock}' command does not reference bundled artifacts."
            )

    # Ensure bundled artifacts exist
    missing_bundles = [
        mock for mock in registry["primary_mocks"]
        if not (bundles_root / f"{mock}.bundled.yaml").exists()
    ]
    for mock in missing_bundles:
        issues.append(f"Bundled artifact missing for mock '{mock}'.")

    report = {
        "status": "success" if not issues else "failure",
        "issues": issues,
    }

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    if issues:
        print("Mock configuration validation FAILED. See report for details.")
        return 1

    print("Mock configuration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
