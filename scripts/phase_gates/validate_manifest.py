#!/usr/bin/env python3
"""
Validate phase_manifest.yaml for structural and referential integrity.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "docs" / "phases" / "phase_manifest.yaml"


class ManifestError(RuntimeError):
    pass


def load_manifest() -> Dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise ManifestError(f"Manifest file not found: {MANIFEST_PATH}")
    with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "phases" not in data:
        raise ManifestError("Manifest must contain a top-level 'phases' list.")
    if not isinstance(data["phases"], list):
        raise ManifestError("'phases' must be a list.")
    return data


def validate_manifest(data: Dict[str, Any]) -> None:
    phases = data["phases"]
    ids: Set[str] = set()
    for phase in phases:
        if "id" not in phase:
            raise ManifestError("All phases must have an 'id'.")
        pid = phase["id"]
        if pid in ids:
            raise ManifestError(f"Duplicate phase id: {pid}")
        ids.add(pid)
        if not phase.get("intent"):
            raise ManifestError(f"Phase {pid} missing intent.")
        if "ci_gate" not in phase or "command" not in phase["ci_gate"]:
            raise ManifestError(f"Phase {pid} missing ci_gate.command.")
        cmd = phase["ci_gate"]["command"]
        if not isinstance(cmd, list) or not all(isinstance(x, str) for x in cmd):
            raise ManifestError(f"Phase {pid} ci_gate.command must be a list of strings.")
        artifacts = phase["ci_gate"].get("artifacts", [])
        if not isinstance(artifacts, list) or not artifacts or not all(isinstance(a, str) for a in artifacts):
            raise ManifestError(f"Phase {pid} ci_gate.artifacts must be a non-empty list of strings.")
        if not phase.get("exit_gates"):
            raise ManifestError(f"Phase {pid} must declare exit_gates.")

    for phase in phases:
        pid = phase["id"]
        prereqs: List[str] = phase.get("prerequisites", [])
        for prereq in prereqs:
            if prereq not in ids:
                raise ManifestError(f"Phase {pid} references missing prerequisite {prereq}")


def main() -> int:
    try:
        data = load_manifest()
        validate_manifest(data)
        print("PHASE MANIFEST VALID")
        return 0
    except ManifestError as exc:
        print(f"Manifest validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
