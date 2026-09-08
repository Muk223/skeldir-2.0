#!/usr/bin/env python3
"""Regenerate the P14 physical-authority manifest from a migrated database.

B2.5-P14 Corrective VII-2. The manifest at
``contracts/trust-api/authority-schema.v1.json`` is the reviewed,
image-shipped expectation that ``/health/ready`` (and every P14 write path
through ``assert_physical_authority``) compares the serving database against.
It must be produced from a real migration replay of the exact tree bytes --
never edited by hand, never learned from a serving/production database.

Usage:
    python scripts/ci/regenerate_b25_p14_authority_manifest.py \
        --dsn postgresql://migration_owner:migration_owner@127.0.0.1:55490/skeldir_vii2_a

The target database must already be migrated to the tree's required head.
After regenerating, the change to the manifest is itself reviewable diff.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.physical_authority import CATALOG_SQL, MANIFEST_PATH  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True)
    args = parser.parse_args()

    import psycopg2

    conn = psycopg2.connect(args.dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM public.alembic_version")
            revisions = sorted(row[0] for row in cur.fetchall())
            cur.execute(CATALOG_SQL)
            objects = [list(row) for row in cur.fetchall()]
    finally:
        conn.close()

    if len(revisions) != 1:
        raise SystemExit(f"manifest requires a single-head database, saw {revisions}")

    manifest = {"revision": revisions[0], "objects": objects}
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"authority_manifest_regenerated revision={revisions[0]} "
          f"objects={len(objects)} path={MANIFEST_PATH}")


if __name__ == "__main__":
    main()
