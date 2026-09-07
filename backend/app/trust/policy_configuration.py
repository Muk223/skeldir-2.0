"""Operator-owned tenant policy publication and read-only Trust derivation.

The deployment publisher credential is kept outside every serving process.
Its database login, not an operator name supplied as data, is the authority.
"""

from __future__ import annotations

import argparse
import json
import os
from uuid import UUID

import psycopg2
from sqlalchemy import text

from app.trust.hash_identity import compute_semantic_truth_hash, compute_signature_hash
from app.trust.policy_defaults import read_only_policy_authority
from app.trust.refusal import tagged_sha256, utc_second

POLICY_STATES = ("blocked", "read_only", "simulation_only", "proposal_required", "approval_required")
LATEST_POLICY_SQL = """
    SELECT id, policy_state, approval_reference, revision, published_by, created_at
      FROM public.trust_tenant_policy_events WHERE tenant_id=:tenant_id
     ORDER BY revision DESC LIMIT 1
"""


async def apply_tenant_policy(session, *, tenant_id: UUID, payload: dict) -> None:
    """Bind operator configuration into the builder before its authority is minted."""
    row = (await session.execute(text(LATEST_POLICY_SQL), {"tenant_id": str(tenant_id)})).mappings().first()
    if row is None:
        return
    state = row["policy_state"]
    if state not in POLICY_STATES:
        raise ValueError("trust_policy_state_ungoverned")
    authority = read_only_policy_authority()
    authority["policy_state"] = state
    authority["reason_code"] = {
        "blocked": "policy_denied", "read_only": "verification_only",
        "simulation_only": "simulation_only", "proposal_required": "approval_required",
        "approval_required": "approval_required",
    }[state]
    if state == "blocked":
        authority["allowed_scopes"] = []
    payload["policy_action_authority"] = authority
    reference = f"urn:skeldir:tenant_policy:{row['id']}"
    payload["provenance_chain"].append({
        "provenance_type": "policy_decision", "authority_table": "trust_tenant_policy_events",
        "source_ref": reference, "source_ref_hash": tagged_sha256({"source_ref": reference}),
        "source_snapshot_hash": tagged_sha256({
            "tenant_id": str(tenant_id), "policy_id": str(row["id"]),
            "revision": row["revision"], "state": state,
            "approval_reference": row["approval_reference"], "published_by": row["published_by"],
        }),
        "observed_at": utc_second(row["created_at"]),
        "display_metadata": {"text_trust_class": "none", "raw_text_sha256": None, "display_transform": "none"},
    })
    payload["semantic_truth_hash"] = compute_semantic_truth_hash(payload)
    payload["signature_hash"] = compute_signature_hash(payload)


def publish_policy(*, tenant_id: UUID, policy_state: str, approval_reference: str) -> str:
    """Append an operator decision using the separately provisioned deployment login."""
    if policy_state not in POLICY_STATES or not 1 <= len(approval_reference) <= 200:
        raise ValueError("trust_policy_configuration_invalid")
    dsn = os.environ["TRUST_POLICY_ADMIN_DATABASE_URL"]
    with psycopg2.connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT session_user")
        if cursor.fetchone()[0] != "app_trust_policy_admin":
            raise ValueError("trust_policy_publisher_principal_required")
        cursor.execute("SELECT set_config('app.current_tenant_id',%s,true)", (str(tenant_id),))
        cursor.execute("""INSERT INTO public.trust_tenant_policy_events
            (tenant_id,policy_state,approval_reference) VALUES (%s,%s,%s) RETURNING id""",
            (str(tenant_id), policy_state, approval_reference))
        return str(cursor.fetchone()[0])


def main() -> None:
    """Publish tenant policy from the production operator job image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", required=True, type=UUID)
    parser.add_argument("--policy-state", required=True, choices=POLICY_STATES)
    parser.add_argument("--approval-reference", required=True)
    args = parser.parse_args()
    print(json.dumps({"policy_id": publish_policy(**vars(args)), "policy_state": args.policy_state}))


if __name__ == "__main__":
    main()
