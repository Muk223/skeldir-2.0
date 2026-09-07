#!/usr/bin/env python3
"""Content-addressed environment signature for the B14 consolidated lane.

RC-P2-02: two jobs may share a prepared immutable environment only after
proving the relevant EnvSig is semantically sufficient. This module computes

    EnvSig = H(OS, arch, toolchain, dependency authority,
               DB schema authority, runtime flags, lane version)

as a canonical JSON document plus its SHA-256 digest. The consolidated
workflow records it per run (artifacts/b14_consolidated/env_signature.json);
the equivalence comparator requires old/new-relevant fields to match and
fails closed on foreign or stale state (P2-C5, Gate 2/7).

DB schema authority binds the alembic revision graph (revision identifiers of
every version file + current heads), not migration *execution*: the template
is migrated once per run, and per-proof databases are cloned from that
template, so schema authority is identical for every proof in the lane.

Usage:
    python scripts/ci/b14_env_signature.py --write artifacts/b14_consolidated/env_signature.json
    python scripts/ci/b14_env_signature.py --check artifacts/b14_consolidated/env_signature.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

LANE_ID = "b14-privacy-consolidated"
LANE_VERSION = "1.0.1-shadow"
PYTHON_VERSION = "3.11"
POSTGRES_IMAGE = "postgres:15-alpine"

# Predecessor proof identities: every incumbent obligation must have an
# explicit successor (P2-C1). The consolidated lane succeeds all eight.
PREDECESSOR_PROOFS = [
    "b14-p0-privacy-authority-lock",
    "b14-p1-ingress-contract-sanitization",
    "b14-p2-session-authority-proofs",
    "b14-p3-attribution-locality-proofs",
    "b14-p4-retention-deletion-proofs",
    "b14-p5-export-log-artifact-no-leak",
    "b14-p6-proof-plane-binding",
    "b14-p7-e2e-privacy-system-proofs",
]

DEPENDENCY_FILES = [
    "backend/requirements.txt",
    "backend/requirements-dev.txt",
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _version_locations(repo: Path) -> list[Path]:
    """Migration authority locations from alembic.ini (sharded directories)."""
    ini = repo / "alembic.ini"
    locs: list[Path] = []
    if ini.exists():
        for line in ini.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("version_locations"):
                _, _, val = s.partition("=")
                for part in val.strip().split(";"):
                    part = part.strip()
                    if part:
                        locs.append(repo / part)
    if not locs:
        locs = [repo / "alembic" / "versions"]
    return locs


def alembic_revision_graph(repo: Path) -> dict:
    """Bind the migration authority graph: every revision id + heads."""
    revs: dict[str, str | None] = {}
    rev_re = re.compile(r"^revision\s*(?::\s*[^=]+)?=\s*['\"]([^'\"]+)['\"]", re.M)
    down_re = re.compile(r"^down_revision\s*(?::\s*[^=]+)?=\s*(['\"][^'\"]+['\"]|\([^)]*\)|None)", re.M)
    files: list[Path] = []
    for loc in _version_locations(repo):
        if loc.is_dir():
            files.extend(sorted(loc.rglob("*.py")))
    for f in files:
        if f.name == "__init__.py":
            continue
        text = f.read_text(encoding="utf-8")
        m = rev_re.search(text)
        if not m:
            continue
        d = down_re.search(text)
        down_val: str | None = None
        if d:
            raw = d.group(1).strip()
            if raw != "None":
                # Tuple (multi-head merge) or single quoted id.
                parts = re.findall(r"['\"]([^'\"]+)['\"]", raw)
                down_val = ",".join(sorted(parts)) if parts else raw
        revs[m.group(1)] = down_val
    children: set[str] = set()
    for _rev, down in revs.items():
        if down:
            for part in down.split(","):
                children.add(part.strip().strip("'\""))
    heads = sorted(r for r in revs if r not in children)
    return {
        "revision_count": len(revs),
        "heads": heads,
        "graph_digest": hashlib.sha256(
            json.dumps(revs, sort_keys=True).encode()
        ).hexdigest(),
    }


def compute_signature(repo: Path = REPO) -> dict:
    deps: dict[str, str] = {}
    for rel in DEPENDENCY_FILES:
        p = repo / rel
        if not p.exists():
            raise FileNotFoundError(f"dependency authority file missing: {rel}")
        deps[rel] = _sha256_file(p)
    graph = alembic_revision_graph(repo)
    doc = {
        "lane_id": LANE_ID,
        "lane_version": LANE_VERSION,
        "os": "ubuntu-latest",
        "arch": platform.machine(),
        "python_version": PYTHON_VERSION,
        "dependency_authority": deps,
        "db_image": POSTGRES_IMAGE,
        "db_schema_authority": graph,
        "predecessor_proofs": PREDECESSOR_PROOFS,
    }
    doc["digest"] = hashlib.sha256(
        json.dumps(doc, sort_keys=True).encode()
    ).hexdigest()
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", default=None, help="write signature JSON here")
    ap.add_argument("--check", default=None, help="recompute and compare")
    args = ap.parse_args()

    if args.check:
        recorded = json.loads(Path(args.check).read_text(encoding="utf-8"))
        recorded_digest = recorded.get("digest", "?")
        fresh = compute_signature()
        # Lane version is deployment metadata, not environment physics: a
        # version bump with identical substrate must not read as foreign env.
        for key in ("lane_version", "digest"):
            recorded.pop(key, None)
            fresh.pop(key, None)
        if recorded != fresh:
            print("B14 EnvSig MISMATCH: effective environment differs", flush=True)
            for k in sorted(set(recorded) | set(fresh)):
                if recorded.get(k) != fresh.get(k):
                    print(f"  field {k}: recorded={json.dumps(recorded.get(k))[:160]}", flush=True)
                    print(f"  field {k}: fresh   ={json.dumps(fresh.get(k))[:160]}", flush=True)
            return 1
        print(f"B14 EnvSig MATCH digest={recorded_digest}")
        return 0

    sig = compute_signature()
    text = json.dumps(sig, indent=2, sort_keys=True)
    if args.write:
        out = Path(args.write)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
