#!/usr/bin/env python3
"""Provision the B14 consolidated lane's isolated databases from one template.

Immutable substrate (shared, content-addressed): one Postgres 15-alpine
service, one dependency install, one `alembic upgrade head` into
`b14_template`.

Mutable proof state (isolated per P2-C6): every predecessor proof runs against
a FRESH logical database cloned with `CREATE DATABASE <proof_db> TEMPLATE
b14_template`. The clone carries the migrated schema and cluster-level roles
but zero proof consequence rows, so each proof starts from the same
empty-consequence state a fresh per-job Postgres service provided.

p6 note: the incumbent p6 job is static (no PG service) but its pytest still
imports backend conftest, whose B0.5.3.3 Gate C requires DATABASE_URL in CI.
The incumbent sets none, so its pytest crashes at import behind `pytest|tee`
(GHA `bash -e` has no pipefail) and the job reports GREEN-VACUOUS (evidence:
run 34047052521 artifact b14-p6-runtime-artifacts, 816 bytes, no JUnit).
The consolidated lane provisions p6 an empty migrated clone too, so the
static suite actually executes here (strictly stronger witness, P2-C1); the
identical fix belongs in ci.yml p6 at DUAL promotion.

Why a template clone instead of per-proof `alembic upgrade head` replays:
roles created by migrations are cluster-level objects, so replaying the full
history per logical database on one shared server fails on the second
`CREATE ROLE`. The template migrates once; clones inherit schema authority
bit-for-bit. Fresh-vs-template semantic equivalence (verdicts plus negative
controls) is proven by the equivalence comparator's red-team corpus, not
asserted here: if cloning ever diverges from fresh construction, the
comparator turns RED and the lane must not promote.

Fail-closed behavior: any error exits non-zero before any proof runs, so a
broken substrate can never present as proof-green (P2-C8).

Usage (inside the consolidated job, after pip install):
    python scripts/ci/b14_provision_template_dbs.py --maintenance-dsn postgresql://postgres:postgres@127.0.0.1:5432/postgres
"""
from __future__ import annotations

import argparse

MAINTENANCE_DB_FALLBACK = "postgres"
TEMPLATE_DB = "b14_template"
# One isolated clone per predecessor proof (p6 included: see module docstring).
PROOF_DBS = {
    "p0": "b14_p0_proof",
    "p1": "b14_p1_proof",
    "p2": "b14_p2_proof",
    "p3": "b14_p3_proof",
    "p4": "b14_p4_proof",
    "p5": "b14_p5_proof",
    "p6": "b14_p6_proof",
    "p7": "b14_p7_proof",
}


def dsn_for(maintenance_dsn: str, dbname: str) -> str:
    """Rewrite the maintenance DSN to address another logical database."""
    # DSNs here are controlled CI construction strings of the form
    # scheme://user:pass@host:port/dbname. Split on the last '/' only.
    head, _, _ = maintenance_dsn.rpartition("/")
    if not head:
        raise ValueError(f"unparseable maintenance DSN: {maintenance_dsn!r}")
    return f"{head}/{dbname}"


def _run_ddl(maintenance_dsn: str, sql: str) -> None:
    import psycopg2  # type: ignore[import-untyped]
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # type: ignore[import-untyped]

    conn = psycopg2.connect(maintenance_dsn)
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.close()


def create_template(maintenance_dsn: str) -> str:
    """Create the empty template database. Migrate it afterwards."""
    _run_ddl(maintenance_dsn, f'CREATE DATABASE "{TEMPLATE_DB}";')
    return dsn_for(maintenance_dsn, TEMPLATE_DB)


def clone_proofs(maintenance_dsn: str) -> dict[str, str]:
    """Clone one fresh consequence-isolated database per DB-backed proof."""
    created: dict[str, str] = {}
    for proof, db in PROOF_DBS.items():
        _run_ddl(maintenance_dsn, f'CREATE DATABASE "{db}" TEMPLATE "{TEMPLATE_DB}";')
        created[proof] = dsn_for(maintenance_dsn, db)
    return created


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--maintenance-dsn", required=True)
    ap.add_argument("--phase", required=True, choices=("create-template", "clone-proofs"),
                    help="create-template runs before `alembic upgrade head`; "
                         "clone-proofs runs after the template is migrated.")
    ap.add_argument("--print-env", action="store_true",
                    help="emit proof DSNs as shell export lines")
    args = ap.parse_args()

    try:
        if args.phase == "create-template":
            template_dsn = create_template(args.maintenance_dsn)
            print(f"B14 template OK db={TEMPLATE_DB}", flush=True)
            if args.print_env:
                print(f"B14_TEMPLATE_DSN={template_dsn}", flush=True)
        else:
            created = clone_proofs(args.maintenance_dsn)
            print(f"B14 clones OK count={len(created)}", flush=True)
            if args.print_env:
                for proof, dsn in sorted(created.items()):
                    print(f"B14_DSN_{proof.upper()}={dsn}", flush=True)
    except Exception as exc:  # fail closed: no partial substrate
        print(f"B14 provision FAILED phase={args.phase}: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
