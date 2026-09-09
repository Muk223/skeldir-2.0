#!/usr/bin/env python3
"""Compare the candidate contract with the production image's loaded bytes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(REPO_ROOT))
FORBIDDEN_IMAGE_ENV = (
    "TRUST_SIGNING_SEED",
    "TRUST_SIGNING_PRIVATE_KEY",
    "MIGRATION_DATABASE_URL",
    "P14_ADMIN_DATABASE_URL",
    "B28_SOLVER_DATABASE_URL",
)


def _run(*command: str) -> str:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def validate(image: str) -> dict[str, object]:
    sys.path.insert(0, str(BACKEND))
    from app.finance_reconciliation.semantic_contract import (  # noqa: PLC0415
        semantic_contract_identity,
    )

    host = semantic_contract_identity().__dict__
    probe = (
        "import json;"
        "from app.finance_reconciliation.semantic_contract import semantic_contract_identity;"
        "print(json.dumps(semantic_contract_identity().__dict__,sort_keys=True))"
    )
    output = _run("docker", "run", "--rm", image, "python", "-c", probe)
    try:
        container = json.loads(output.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"container_contract_identity_malformed:{output}") from exc
    if container != host:
        raise RuntimeError(
            f"container_contract_identity_mismatch:host={host}:container={container}"
        )
    inspect = json.loads(_run("docker", "image", "inspect", image))[0]
    environment = inspect.get("Config", {}).get("Env", []) or []
    exposed = [
        item for item in environment if item.split("=", 1)[0] in FORBIDDEN_IMAGE_ENV
    ]
    if exposed:
        raise RuntimeError(f"container_forbidden_authority_env:{exposed}")
    return {
        "image": image,
        "image_id": inspect["Id"],
        "repo_digests": inspect.get("RepoDigests", []),
        "host_contract_identity": host,
        "container_contract_identity": container,
        "forbidden_authority_env_present": [],
        "boot_authority": "exact-SHA C19 topology attested by independent producer",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--evidence-out", type=Path)
    args = parser.parse_args()
    try:
        details = validate(args.image)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"B26_P1_CONTAINER_EQUIVALENCE_FAIL {exc}")
        return 1
    if args.evidence_out:
        from scripts.ci.b26_p1_evidence import write_evidence_cell  # noqa: PLC0415

        write_evidence_cell(
            args.evidence_out,
            gate_id="B26-P1-G3-G10-CONTAINER-EQUIVALENCE",
            producer="b26-p1-container-equivalence",
            scenario_id="candidate-production-image",
            falsifier_id="B26-P1-NC-07",
            details=details,
        )
    print("B26_P1_CONTAINER_EQUIVALENCE_PASS")
    print(json.dumps(details, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
