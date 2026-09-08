"""B2.5-P14 Corrective VII-2 successor proofs: exact issuance selection.

H-VII2-01. Two separate issuances may share one logical ``envelope_id``
(the builder derives it from tenant + subject, not from issuance time), so a
request selecting its source by ``envelope_id`` alone can ambiguously identify
an older issuance. The VII contract therefore requires the caller to also
supply the final artifact hash, and the durable layer to resolve the exact
signer-backed issuance deterministically:

    request naming A + hash(A)  ->  A selected
    request naming B + hash(B)  ->  B selected
    unknown final hash          ->  refused (no fallback to latest/first)
    cross-tenant matching hash  ->  refused

These proofs run at the database seam (the view, the triggers, the library
conduction path) without a C19 topology. The HTTP end of the same law --
exact selector wiring through contract, handler, and read model -- is proved
by the C19 positive/negative legs. What is proved here is that the seam the
HTTP layer stands on cannot silently alias one issuance for another.

Issuance shape honesty. The R4 fixture aligns audit-stage and final
identities (it persists ``compute(signed)`` as the history hash). Production
does not: the P7 audit ledger records provisional hashes and the signer
produces the final artifact afterwards. The helper below therefore persists a
production-shaped lineage -- a distinct provisional audit-stage hash alongside
the final artifact -- so the mapping under test is the real one, not an
aligned substitute.
"""

from __future__ import annotations

import copy
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import psycopg2
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.simulation.consequence_custody import (
    B28_REQUEST_DATABASE_URL_ENV,
    B28_REQUEST_PRINCIPAL,
    B28_SOLVER_DATABASE_URL_ENV,
    B28_SOLVER_PRINCIPAL,
)
from app.simulation.contract import ChannelEvidence
from app.simulation.persistence import conduct_requested_simulation
from app.simulation.requester_identity import REQUESTED_BY_PREFIX
from app.trust.canonicalization import (
    canonicalize_envelope_payload,
    canonicalize_signature_material,
)
from app.trust.hash_identity import compute_envelope_payload_hash
from app.trust.key_registry import TrustKeyRegistry, TrustSigningKey
from app.trust.machine_identity import generate_machine_token
from app.trust.refusal import tagged_sha256
from app.trust.signing import (
    decode_ed25519_signature,
    encode_ed25519_signature,
    prepare_payload_for_signing,
)
from app.trust.verification import verify_trust_envelope


pytestmark = pytest.mark.skipif(
    os.getenv("SKELDIR_B25_P14_GATE0_PROOF") != "1",
    reason="P14 VII-2 selector proofs require a provisioned production role graph",
)


REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "contracts/trust-api/examples"

SUFFICIENT_CHANNELS = (
    ChannelEvidence("google_ads", 400_000, 12),
    ChannelEvidence("meta_ads", 250_000, 7),
    ChannelEvidence("email", 100_000, 3),
)


def _admin_dsn() -> str:
    for name in (
        "P14_ADMIN_DATABASE_URL",
        "C21_ADMIN_DATABASE_URL",
        "C20_ADMIN_DATABASE_URL",
        "MIGRATION_DATABASE_URL",
    ):
        value = os.getenv(name, "").strip()
        if value:
            return value.replace("postgresql+psycopg2://", "postgresql://")
    raise RuntimeError("P14_ADMIN_DATABASE_URL is required for the VII-2 proofs")


def _role_connection(role: str):
    parts = urlsplit(_admin_dsn())
    conn = psycopg2.connect(
        dbname=parts.path.lstrip("/"),
        host=parts.hostname,
        port=parts.port or 5432,
        user=role,
        password=os.getenv(f"P14_{role.upper()}_PASSWORD", role),
    )
    conn.autocommit = False
    return conn


def _dsn_for_principal(principal: str) -> str:
    parts = urlsplit(_admin_dsn())
    return (
        f"postgresql://{principal}:{principal}@{parts.hostname}:"
        f"{parts.port or 5432}{parts.path}"
    )


@pytest.fixture(autouse=True)
def _b28_consequence_custody(monkeypatch):
    monkeypatch.setenv(
        B28_REQUEST_DATABASE_URL_ENV, _dsn_for_principal(B28_REQUEST_PRINCIPAL)
    )
    monkeypatch.setenv(
        B28_SOLVER_DATABASE_URL_ENV, _dsn_for_principal(B28_SOLVER_PRINCIPAL)
    )
    yield


def _digest() -> str:
    return "sha256:" + uuid.uuid4().hex + uuid.uuid4().hex


def _bind_tenant(cursor, tenant_id) -> None:
    cursor.execute(
        "SELECT set_config('app.current_tenant_id', %s, false)", (str(tenant_id),)
    )


def _seed_tenant(cursor) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    label = tenant_id.hex[:8]
    cursor.execute(
        "INSERT INTO public.tenants (id, name, api_key_hash, notification_email)"
        " VALUES (%s, %s, %s, %s)",
        (
            str(tenant_id),
            f"p14vii2-{label}",
            uuid.uuid4().hex,
            f"p14vii2-{label}@example.invalid",
        ),
    )
    return tenant_id


def _seed_agent_credential(cursor, tenant_id) -> dict[str, str]:
    secret = generate_machine_token()
    client_id = uuid.uuid4()
    credential_id = uuid.uuid4()
    cursor.execute(
        "INSERT INTO public.agent_clients (id, tenant_id, client_name,"
        " client_display_hash, audience, status)"
        " VALUES (%s,%s,%s,%s,'trust-api','active')",
        (str(client_id), str(tenant_id), f"p14vii2-{client_id.hex[:8]}", _digest()),
    )
    cursor.execute(
        "INSERT INTO public.agent_service_credentials (id, tenant_id,"
        " agent_client_id, token_prefix, token_hash, status)"
        " VALUES (%s,%s,%s,%s,%s,'active')",
        (
            str(credential_id),
            str(tenant_id),
            str(client_id),
            secret.token_prefix,
            secret.token_hash,
        ),
    )
    return {
        "token": secret.plaintext,
        "agent_client_id": str(client_id),
        "credential_id": str(credential_id),
        "requested_by": f"{REQUESTED_BY_PREFIX}{client_id}",
    }


def _publish_policy(tenant_id, policy_state: str) -> None:
    from app.trust.policy_configuration import publish_policy

    previous = os.environ.get("TRUST_POLICY_ADMIN_DATABASE_URL")
    os.environ["TRUST_POLICY_ADMIN_DATABASE_URL"] = _dsn_for_principal(
        "app_trust_policy_admin"
    )
    try:
        publish_policy(
            tenant_id=tenant_id,
            policy_state=policy_state,
            approval_reference="vii2-successor-proof",
        )
    finally:
        if previous is None:
            os.environ.pop("TRUST_POLICY_ADMIN_DATABASE_URL", None)
        else:
            os.environ["TRUST_POLICY_ADMIN_DATABASE_URL"] = previous


def _sign_envelope(
    tenant_id,
    *,
    policy_state: str = "simulation_only",
    verified_revenue_minor: int | None = None,
) -> dict[str, Any]:
    payload = json.loads(
        (EXAMPLES / "revenue_claim_valid_with_verified_revenue_minor.json").read_text(
            encoding="utf-8"
        )
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload["created_at"] = now.isoformat().replace("+00:00", "Z")
    payload["valid_until"] = (now + timedelta(days=30)).isoformat().replace(
        "+00:00", "Z"
    )
    payload["tenant_id_hash"] = tagged_sha256({"tenant_id": str(tenant_id)})
    payload["policy_action_authority"]["policy_state"] = policy_state
    if verified_revenue_minor is not None:
        payload["verified_revenue_minor"] = verified_revenue_minor

    private_key = Ed25519PrivateKey.generate()
    key = TrustSigningKey(
        kid=f"kid:p14vii2-{uuid.uuid4().hex[:8]}",
        algorithm="ed25519",
        public_key=private_key.public_key(),
        private_key=private_key,
        state="active",
        valid_from=now - timedelta(days=1),
    )
    registry = TrustKeyRegistry(keys=(key,))
    prepared = prepare_payload_for_signing(
        payload, signing_key_id=key.kid, signing_algorithm="ed25519"
    )
    signature = private_key.sign(canonicalize_signature_material(prepared))
    signed = copy.deepcopy(prepared)
    signed["signature"] = encode_ed25519_signature(signature)
    canonicalize_envelope_payload(signed)
    verification = verify_trust_envelope(signed, key_registry=registry.public_only())
    assert verification.verification_status == "verified", verification
    return signed


def _conduct_production_shaped_issuance(
    tenant_id, signed: dict[str, Any], *, provisional_hash: str
) -> dict[str, str]:
    """Persist a production-shaped lineage: provisional audit hash != final.

    ``provisional_hash`` stands in for the P7 audit-stage hash the production
    path records before signing. It is deliberately distinct from the final
    artifact hash, which is the invariant production guarantees and the
    aligned fixture does not.
    """

    final_hash = compute_envelope_payload_hash(signed)
    assert provisional_hash != final_hash, "the premise requires distinct stages"
    material = {
        "audit_ref": f"urn:skeldir:audit:p14vii2-{uuid.uuid4().hex}",
        "request_identity_hash": _digest(),
        "idempotency_key_hash": _digest(),
        "subject_type": signed["subject_type"],
        "subject_ref_hash": signed["subject_ref_hash"],
        "envelope_hash": provisional_hash,
        "semantic_truth_hash": signed["semantic_truth_hash"],
        "policy_state": signed["policy_action_authority"]["policy_state"],
        "audit_hash": _digest(),
        "signature_hash": signed["signature_hash"],
        "signing_key_id": signed["signing_key_id"],
    }

    user = _role_connection("app_user")
    try:
        with user.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            cursor.execute(
                "INSERT INTO public.trust_access_log (tenant_id, event_type, status,"
                " request_identity_hash, idempotency_key_hash, subject_type,"
                " subject_ref_hash, envelope_hash, semantic_truth_hash, policy_state,"
                " audit_ref, audit_hash, evidence_refs_allowed, issuance_state)"
                " VALUES (%s,'issuance','success',%s,%s,%s,%s,%s,%s,%s,%s,%s,true,"
                "'authorized')",
                (
                    str(tenant_id),
                    material["request_identity_hash"],
                    material["idempotency_key_hash"],
                    material["subject_type"],
                    material["subject_ref_hash"],
                    material["envelope_hash"],
                    material["semantic_truth_hash"],
                    material["policy_state"],
                    material["audit_ref"],
                    material["audit_hash"],
                ),
            )
        user.commit()
    finally:
        user.close()

    attempt_id = uuid.uuid4()
    issuer = _role_connection("app_trust_issuer")
    try:
        with issuer.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            cursor.execute(
                "UPDATE public.trust_access_log SET issuance_state='signing',"
                " issuance_attempted_at=now(), issuance_attempt_count=1"
                " WHERE tenant_id=%s AND audit_ref=%s",
                (str(tenant_id), material["audit_ref"]),
            )
            cursor.execute(
                "INSERT INTO public.trust_issuance_attempts"
                " (id, tenant_id, audit_ref, attempt_number, attempt_state)"
                " VALUES (%s,%s,%s,1,'signing')",
                (str(attempt_id), str(tenant_id), material["audit_ref"]),
            )
        issuer.commit()
    finally:
        issuer.close()

    signer = _role_connection("app_trust_signer")
    try:
        with signer.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            cursor.execute(
                "UPDATE public.trust_issuance_attempts"
                " SET attempt_state='signature_known', signature_known_at=now(),"
                " signing_key_id=%s, signature_hash=%s,"
                " signature=decode(%s,'hex'), signed_envelope_hash=%s,"
                " signed_envelope=%s::jsonb"
                " WHERE tenant_id=%s AND id=%s RETURNING signature_known_at",
                (
                    material["signing_key_id"],
                    material["signature_hash"],
                    decode_ed25519_signature(signed["signature"]).hex(),
                    final_hash,
                    json.dumps(signed),
                    str(tenant_id),
                    str(attempt_id),
                ),
            )
            known_at = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE public.trust_access_log SET issuance_state='signature_known',"
                " known_signature_at=%s, issued_attempt_id=%s"
                " WHERE tenant_id=%s AND audit_ref=%s",
                (known_at, str(attempt_id), str(tenant_id), material["audit_ref"]),
            )
        signer.commit()
    finally:
        signer.close()

    issuer = _role_connection("app_trust_issuer")
    try:
        with issuer.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            cursor.execute(
                "UPDATE public.trust_access_log AS log"
                "   SET issuance_state='issued', issued_at=now(),"
                "       issued_signing_key_id=attempt.signing_key_id,"
                "       issued_signature_hash=attempt.signature_hash,"
                "       issued_signature=attempt.signature,"
                "       issued_envelope=attempt.signed_envelope"
                "  FROM public.trust_issuance_attempts AS attempt"
                " WHERE log.tenant_id=%s AND log.audit_ref=%s"
                "   AND attempt.id=log.issued_attempt_id"
                "   AND attempt.tenant_id=log.tenant_id",
                (str(tenant_id), material["audit_ref"]),
            )
            cursor.execute(
                "UPDATE public.trust_issuance_attempts SET attempt_state='issued',"
                " issued_at=now() WHERE tenant_id=%s AND id=%s",
                (str(tenant_id), str(attempt_id)),
            )
            cursor.execute(
                "INSERT INTO public.trust_envelope_issuance_log (tenant_id,"
                " access_audit_ref, idempotency_key_hash, subject_type,"
                " subject_ref_hash, envelope_hash, semantic_truth_hash, policy_state,"
                " audit_ref, audit_hash, status)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'success')",
                (
                    str(tenant_id),
                    material["audit_ref"],
                    material["idempotency_key_hash"],
                    material["subject_type"],
                    material["subject_ref_hash"],
                    material["envelope_hash"],
                    material["semantic_truth_hash"],
                    material["policy_state"],
                    material["audit_ref"],
                    material["audit_hash"],
                ),
            )
        issuer.commit()
    finally:
        issuer.close()
    material["final_envelope_hash"] = final_hash
    return material


def _view_lookup(cursor, tenant_id, envelope_id, final_hash):
    cursor.execute(
        "SELECT envelope_hash, final_envelope_hash, semantic_truth_hash,"
        " policy_state FROM public.trust_final_issuance_identity"
        " WHERE tenant_id=%s AND source_envelope_id=%s AND final_envelope_hash=%s",
        (str(tenant_id), envelope_id, final_hash),
    )
    return cursor.fetchall()


def _census(admin_cursor, tenant_id) -> tuple[int, int, int, int]:
    admin_cursor.execute(
        "SELECT (SELECT count(*) FROM public.b28_simulation_requests"
        " WHERE tenant_id=%s), (SELECT count(*) FROM public.b28_simulation_results"
        " WHERE tenant_id=%s), (SELECT count(*) FROM public.b28_proposals"
        " WHERE tenant_id=%s), (SELECT count(*) FROM public.b28_request_authentications"
        " WHERE tenant_id=%s)",
        (str(tenant_id),) * 4,
    )
    return tuple(int(v) for v in admin_cursor.fetchone())


def _setup_tenant_with_credential() -> tuple[uuid.UUID, dict[str, str]]:
    admin = psycopg2.connect(_admin_dsn())
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            tenant_id = _seed_tenant(cursor)
            _bind_tenant(cursor, tenant_id)
            credential = _seed_agent_credential(cursor, tenant_id)
    finally:
        admin.close()
    return tenant_id, credential


def test_vii2_final_selector_disambiguates_shared_envelope_id() -> None:
    """H-VII2-01: the final artifact hash deterministically selects the
    intended issuance when two issuances share one logical envelope_id."""
    tenant_id, credential = _setup_tenant_with_credential()
    _publish_policy(tenant_id, "simulation_only")

    signed_a = _sign_envelope(tenant_id, verified_revenue_minor=111_00)
    signed_b = _sign_envelope(tenant_id, verified_revenue_minor=222_00)
    assert signed_a["envelope_id"] == signed_b["envelope_id"], (
        "the premise requires one shared logical envelope identity"
    )
    envelope_id = signed_a["envelope_id"]
    final_a = compute_envelope_payload_hash(signed_a)
    final_b = compute_envelope_payload_hash(signed_b)
    assert final_a != final_b, "distinct issuances must have distinct final hashes"

    issuance_a = _conduct_production_shaped_issuance(
        tenant_id, signed_a, provisional_hash=_digest()
    )
    issuance_b = _conduct_production_shaped_issuance(
        tenant_id, signed_b, provisional_hash=_digest()
    )
    assert issuance_a["envelope_hash"] != issuance_b["envelope_hash"]
    assert issuance_a["envelope_hash"] != final_a
    assert issuance_b["envelope_hash"] != final_b

    admin = psycopg2.connect(_admin_dsn())
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            rows_a = _view_lookup(cursor, tenant_id, envelope_id, final_a)
            rows_b = _view_lookup(cursor, tenant_id, envelope_id, final_b)
            assert len(rows_a) == 1, rows_a
            assert len(rows_b) == 1, rows_b
            assert rows_a[0][0] == issuance_a["envelope_hash"]
            assert rows_b[0][0] == issuance_b["envelope_hash"]
            assert rows_a[0][1] == final_a and rows_b[0][1] == final_b
            # Unknown final hash: no fallback to latest, first, or any row.
            assert _view_lookup(cursor, tenant_id, envelope_id, _digest()) == []
    finally:
        admin.close()

    conducted_a = conduct_requested_simulation(
        envelope=signed_a,
        tenant_id=str(tenant_id),
        presented_token=credential["token"],
        source_issuance_envelope_hash=issuance_a["envelope_hash"],
        total_budget_minor=1_000_000,
        currency="USD",
        channels=SUFFICIENT_CHANNELS,
        request_ref=f"req_vii2_a_{uuid.uuid4().hex}",
    )
    conducted_b = conduct_requested_simulation(
        envelope=signed_b,
        tenant_id=str(tenant_id),
        presented_token=credential["token"],
        source_issuance_envelope_hash=issuance_b["envelope_hash"],
        total_budget_minor=1_000_000,
        currency="USD",
        channels=SUFFICIENT_CHANNELS,
        request_ref=f"req_vii2_b_{uuid.uuid4().hex}",
    )
    assert conducted_a["identifiers"].get("persisted") == "true"
    assert conducted_b["identifiers"].get("persisted") == "true"

    admin = psycopg2.connect(_admin_dsn())
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(
                "SELECT source_issuance_envelope_hash FROM"
                " public.b28_simulation_requests WHERE tenant_id=%s"
                " ORDER BY requested_at",
                (str(tenant_id),),
            )
            bound = [row[0] for row in cursor.fetchall()]
    finally:
        admin.close()
    assert bound == [issuance_a["envelope_hash"], issuance_b["envelope_hash"]], bound
    print("VII2_H01_EXACT_ISSUANCE_SELECTION_PASS")


def test_vii2_foreign_selector_and_unknown_issuance_refuse() -> None:
    """H-VII2-01 negative legs: unknown issuance hash and cross-tenant
    selectors refuse with no durable side effects and no silent fallback."""
    tenant_id, credential = _setup_tenant_with_credential()
    other_id, _ = _setup_tenant_with_credential()
    _publish_policy(tenant_id, "simulation_only")

    signed = _sign_envelope(tenant_id, verified_revenue_minor=333_00)
    issuance = _conduct_production_shaped_issuance(
        tenant_id, signed, provisional_hash=_digest()
    )

    admin = psycopg2.connect(_admin_dsn())
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            assert (
                _view_lookup(cursor, other_id, signed["envelope_id"],
                             compute_envelope_payload_hash(signed))
                == []
            ), "a matching final hash must not resolve across tenants"
            before = _census(cursor, tenant_id)

        with pytest.raises(Exception, match="b28_request_requires_durable_issuance"):
            conduct_requested_simulation(
                envelope=signed,
                tenant_id=str(tenant_id),
                presented_token=credential["token"],
                source_issuance_envelope_hash=_digest(),
                total_budget_minor=1_000_000,
                currency="USD",
                channels=SUFFICIENT_CHANNELS,
                request_ref=f"req_vii2_unknown_{uuid.uuid4().hex}",
            )

        with admin.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            assert _census(cursor, tenant_id) == before, (
                "a refused selection must leave no request, result, proposal,"
                " or witness"
            )
            assert issuance["envelope_hash"] is not None
    finally:
        admin.close()
    print("VII2_H01_NEGATIVE_SELECTION_PASS")


def test_vii2_policy_revocation_refuses_without_side_effects() -> None:
    """H-VII2-04/H-VII2-03: request-time live policy governs alongside the
    issuance-time snapshot. Revoking to read_only after issuance refuses new
    simulation; a read_only issuance is never raised by a later grant."""
    tenant_id, credential = _setup_tenant_with_credential()
    _publish_policy(tenant_id, "simulation_only")
    signed = _sign_envelope(tenant_id, verified_revenue_minor=444_00)
    issuance = _conduct_production_shaped_issuance(
        tenant_id, signed, provisional_hash=_digest()
    )

    first = conduct_requested_simulation(
        envelope=signed,
        tenant_id=str(tenant_id),
        presented_token=credential["token"],
        source_issuance_envelope_hash=issuance["envelope_hash"],
        total_budget_minor=1_000_000,
        currency="USD",
        channels=SUFFICIENT_CHANNELS,
        request_ref=f"req_vii2_rev_ok_{uuid.uuid4().hex}",
    )
    assert first["identifiers"].get("persisted") == "true"

    admin = psycopg2.connect(_admin_dsn())
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            before = _census(cursor, tenant_id)

        _publish_policy(tenant_id, "read_only")
        with pytest.raises(Exception, match="policy_forbids|current_policy_forbids"):
            conduct_requested_simulation(
                envelope=signed,
                tenant_id=str(tenant_id),
                presented_token=credential["token"],
                source_issuance_envelope_hash=issuance["envelope_hash"],
                total_budget_minor=1_000_000,
                currency="USD",
                channels=SUFFICIENT_CHANNELS,
                request_ref=f"req_vii2_revoked_{uuid.uuid4().hex}",
            )

        with admin.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            assert _census(cursor, tenant_id) == before

        _publish_policy(tenant_id, "simulation_only")
        read_only_signed = _sign_envelope(
            tenant_id, policy_state="read_only", verified_revenue_minor=555_00
        )
        read_only_issuance = _conduct_production_shaped_issuance(
            tenant_id, read_only_signed, provisional_hash=_digest()
        )
        with pytest.raises(Exception, match="policy_forbids"):
            conduct_requested_simulation(
                envelope=read_only_signed,
                tenant_id=str(tenant_id),
                presented_token=credential["token"],
                source_issuance_envelope_hash=read_only_issuance["envelope_hash"],
                total_budget_minor=1_000_000,
                currency="USD",
                channels=SUFFICIENT_CHANNELS,
                request_ref=f"req_vii2_stale_{uuid.uuid4().hex}",
            )
        with admin.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            assert _census(cursor, tenant_id) == before, (
                "a read_only source must not gain authority from a later grant"
            )
    finally:
        admin.close()
    print("VII2_H04_POLICY_REVOCATION_PASS")


def test_vii2_duplicate_request_ref_is_not_a_second_request() -> None:
    """H-VII2-07: repeating one external request reference refuses; a new
    reference over the same Trust and budget is a distinct lawful request."""
    tenant_id, credential = _setup_tenant_with_credential()
    _publish_policy(tenant_id, "simulation_only")
    signed = _sign_envelope(tenant_id, verified_revenue_minor=666_00)
    issuance = _conduct_production_shaped_issuance(
        tenant_id, signed, provisional_hash=_digest()
    )
    ref = f"req_vii2_dup_{uuid.uuid4().hex}"
    conducted = conduct_requested_simulation(
        envelope=signed,
        tenant_id=str(tenant_id),
        presented_token=credential["token"],
        source_issuance_envelope_hash=issuance["envelope_hash"],
        total_budget_minor=1_000_000,
        currency="USD",
        channels=SUFFICIENT_CHANNELS,
        request_ref=ref,
    )
    assert conducted["identifiers"].get("persisted") == "true"

    with pytest.raises(Exception):
        conduct_requested_simulation(
            envelope=signed,
            tenant_id=str(tenant_id),
            presented_token=credential["token"],
            source_issuance_envelope_hash=issuance["envelope_hash"],
            total_budget_minor=1_000_000,
            currency="USD",
            channels=SUFFICIENT_CHANNELS,
            request_ref=ref,
        )

    second = conduct_requested_simulation(
        envelope=signed,
        tenant_id=str(tenant_id),
        presented_token=credential["token"],
        source_issuance_envelope_hash=issuance["envelope_hash"],
        total_budget_minor=1_000_000,
        currency="USD",
        channels=SUFFICIENT_CHANNELS,
        request_ref=f"req_vii2_dup2_{uuid.uuid4().hex}",
    )
    assert second["identifiers"].get("persisted") == "true"
    assert second["request_id"] != conducted["request_id"]

    admin = psycopg2.connect(_admin_dsn())
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            assert _census(cursor, tenant_id) == (2, 2, 2, 2), _census(
                cursor, tenant_id
            )
    finally:
        admin.close()
    print("VII2_H07_DUPLICATE_SEMANTICS_PASS")


def test_vii2_witness_freshness_is_wall_clock() -> None:
    """Temporal integrity: the possession witness records wall-clock time,
    not transaction-start time, and the 900-second fence fires on age.

    Two mints separated by real elapsed time inside ONE transaction must
    differ (``now()`` would stamp both identically). An aged witness must
    refuse at consumption while a fresh one is admitted.
    """
    import time

    from app.simulation.admission import compute_input_snapshot_hash
    from app.simulation.contract import SimulationRequest
    from app.simulation.solver import SOLVER_PROFILE
    from app.simulation.sufficiency import (
        SUFFICIENCY_POLICY_VERSION,
        adjudicate_sufficiency,
    )

    tenant_id, credential = _setup_tenant_with_credential()
    _publish_policy(tenant_id, "simulation_only")
    signed = _sign_envelope(tenant_id, verified_revenue_minor=888_00)
    issuance = _conduct_production_shaped_issuance(
        tenant_id, signed, provisional_hash=_digest()
    )

    def _mint(cursor, ref: str) -> tuple[str, Any]:
        cursor.execute(
            "SELECT public.b28_authenticate_request_possession("
            "%s::uuid, %s, %s, %s, %s)",
            (
                str(tenant_id),
                credential["token"],
                ref,
                issuance["envelope_hash"],
                "sha256:" + "0" * 64,
            ),
        )
        witness_id = str(cursor.fetchone()[0])
        cursor.execute(
            "SELECT authenticated_at FROM public.b28_request_authentications"
            " WHERE id = %s",
            (witness_id,),
        )
        return witness_id, cursor.fetchone()[0]

    requester = _role_connection(B28_REQUEST_PRINCIPAL)
    try:
        with requester.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            _, at_a = _mint(cursor, f"req_vii2_wall_a_{uuid.uuid4().hex}")
            time.sleep(1.5)
            _, at_b = _mint(cursor, f"req_vii2_wall_b_{uuid.uuid4().hex}")
        requester.commit()
    finally:
        requester.close()
    assert (at_b - at_a).total_seconds() >= 1.0, (
        f"witness timestamps did not advance with the wall clock: {at_a} {at_b}"
    )

    adjudication = adjudicate_sufficiency(SUFFICIENT_CHANNELS)
    assert adjudication.sufficient
    probe = SimulationRequest(
        request_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        requested_by=credential["requested_by"],
        source_envelope_id=signed["envelope_id"],
        source_semantic_truth_hash=signed["semantic_truth_hash"],
        total_budget_minor=1_000_000,
        currency="USD",
        channels=SUFFICIENT_CHANNELS,
        requested_at="pending",
    )
    snapshot_hash = compute_input_snapshot_hash(probe)
    evidence_json = json.dumps(
        [
            {
                "channel_id": c.channel_id,
                "verified_revenue_minor": c.verified_revenue_minor,
                "conversion_count": c.conversion_count,
            }
            for c in SUFFICIENT_CHANNELS
        ],
        separators=(",", ":"),
    )

    def _insert_with_witness(cursor, ref: str, witness_id: str) -> None:
        cursor.execute(
            "INSERT INTO public.b28_simulation_requests (tenant_id, request_ref,"
            " requested_by, requested_by_agent_client_id,"
            " requested_by_credential_id, request_authority_principal,"
            " request_authentication_id, source_envelope_id,"
            " source_semantic_truth_hash, source_issuance_envelope_hash,"
            " input_snapshot_hash, total_budget_minor, currency, channel_count,"
            " channel_evidence, solver_profile, sufficiency_policy_version,"
            " sufficiency_verdict, sufficiency_reasons, observed_channels,"
            " observed_conversions, observed_revenue_minor)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,"
            " %s,%s,%s,%s,%s,%s,%s)",
            (
                str(tenant_id),
                ref,
                credential["requested_by"],
                credential["agent_client_id"],
                credential["credential_id"],
                B28_REQUEST_PRINCIPAL,
                witness_id,
                signed["envelope_id"],
                signed["semantic_truth_hash"],
                issuance["envelope_hash"],
                snapshot_hash,
                1_000_000,
                "USD",
                len(SUFFICIENT_CHANNELS),
                evidence_json,
                SOLVER_PROFILE,
                SUFFICIENCY_POLICY_VERSION,
                adjudication.sufficient,
                list(adjudication.reasons),
                adjudication.observed_channels,
                adjudication.observed_conversions,
                adjudication.observed_revenue_minor,
            ),
        )

    requester = _role_connection(B28_REQUEST_PRINCIPAL)
    try:
        with requester.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            aged_ref = f"req_vii2_aged_{uuid.uuid4().hex}"
            cursor.execute(
                "SELECT public.b28_authenticate_request_possession("
                "%s::uuid, %s, %s, %s, %s)",
                (
                    str(tenant_id),
                    credential["token"],
                    aged_ref,
                    issuance["envelope_hash"],
                    snapshot_hash,
                ),
            )
            aged_witness = str(cursor.fetchone()[0])
        requester.commit()
    finally:
        requester.close()

    admin = psycopg2.connect(_admin_dsn())
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(
                "UPDATE public.b28_request_authentications SET authenticated_at ="
                " clock_timestamp() - interval '901 seconds' WHERE id = %s",
                (aged_witness,),
            )
    finally:
        admin.close()

    requester = _role_connection(B28_REQUEST_PRINCIPAL)
    try:
        with requester.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            with pytest.raises(
                Exception, match="b28_request_possession_witness_expired"
            ):
                _insert_with_witness(cursor, aged_ref, aged_witness)
            requester.rollback()
            # Rollback reverts even session-level set_config made inside the
            # aborted transaction, so the tenant binding must be re-established.
            _bind_tenant(cursor, tenant_id)

            fresh_ref = f"req_vii2_fresh_{uuid.uuid4().hex}"
            cursor.execute(
                "SELECT public.b28_authenticate_request_possession("
                "%s::uuid, %s, %s, %s, %s)",
                (
                    str(tenant_id),
                    credential["token"],
                    fresh_ref,
                    issuance["envelope_hash"],
                    snapshot_hash,
                ),
            )
            fresh_witness = str(cursor.fetchone()[0])
            _insert_with_witness(cursor, fresh_ref, fresh_witness)
            requester.rollback()
    finally:
        requester.close()
    print("VII2_TEMPORAL_WALL_CLOCK_PASS")


def test_vii2_final_mapping_is_not_writable() -> None:
    """H-VII2-09: the audit-to-final mapping is a derived view, not a mutable
    authority seam. No runtime principal can insert, update, or delete it."""
    tenant_id, _ = _setup_tenant_with_credential()
    _publish_policy(tenant_id, "simulation_only")
    signed = _sign_envelope(tenant_id, verified_revenue_minor=777_00)
    _conduct_production_shaped_issuance(
        tenant_id, signed, provisional_hash=_digest()
    )
    for role in ("app_user", "app_b28_requester", "app_b28_solver",
                 "app_trust_issuer"):
        conn = _role_connection(role)
        try:
            with conn.cursor() as cursor:
                _bind_tenant(cursor, tenant_id)
                with pytest.raises(Exception):
                    cursor.execute(
                        "UPDATE public.trust_final_issuance_identity"
                        " SET policy_state='simulation_only'"
                        " WHERE tenant_id=%s",
                        (str(tenant_id),),
                    )
                conn.rollback()
                with pytest.raises(Exception):
                    cursor.execute(
                        "DELETE FROM public.trust_final_issuance_identity"
                        " WHERE tenant_id=%s",
                        (str(tenant_id),),
                    )
                conn.rollback()
        finally:
            conn.close()
    print("VII2_H09_MAPPING_IMMUTABLE_PASS")


def test_vii2_policy_table_is_append_only_and_least_privilege() -> None:
    """H-VII2-10: ordinary runtime principals cannot invent simulation
    authority; the publisher cannot rewrite history; the default stays
    read_only with no governing row."""
    tenant_id, _ = _setup_tenant_with_credential()
    for role in ("app_user", "app_b28_requester", "app_b28_solver", "app_worker"):
        conn = _role_connection(role)
        try:
            with conn.cursor() as cursor:
                _bind_tenant(cursor, tenant_id)
                with pytest.raises(Exception):
                    cursor.execute(
                        "INSERT INTO public.trust_tenant_policy_events"
                        " (tenant_id, policy_state, approval_reference)"
                        " VALUES (%s,'simulation_only','forged')",
                        (str(tenant_id),),
                    )
                conn.rollback()
        finally:
            conn.close()

    _publish_policy(tenant_id, "simulation_only")
    admin = psycopg2.connect(_admin_dsn())
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            cursor.execute(
                "SELECT policy_state FROM public.trust_tenant_policy_events"
                " WHERE tenant_id=%s ORDER BY revision DESC LIMIT 1",
                (str(tenant_id),),
            )
            assert cursor.fetchone()[0] == "simulation_only"
    finally:
        admin.close()

    publisher = _role_connection("app_trust_policy_admin")
    try:
        with publisher.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            # Least privilege first: the publisher holds INSERT/SELECT only,
            # so history rewriting is refused before any trigger is reached.
            with pytest.raises(Exception, match="permission denied"):
                cursor.execute(
                    "UPDATE public.trust_tenant_policy_events SET policy_state='read_only'"
                    " WHERE tenant_id=%s",
                    (str(tenant_id),),
                )
            publisher.rollback()
            with pytest.raises(Exception):
                cursor.execute(
                    "INSERT INTO public.trust_tenant_policy_events"
                    " (tenant_id, policy_state, approval_reference, published_by)"
                    " VALUES (%s,'simulation_only','forged','app_user')",
                    (str(tenant_id),),
                )
            publisher.rollback()
    finally:
        publisher.close()

    # The append-only trigger is the second layer: even the table owner,
    # who bypasses grants, cannot rewrite or erase governing history
    # (tenant-cascade deletes excepted, so FK discipline still holds).
    owner = _role_connection("migration_owner")
    try:
        with owner.cursor() as cursor:
            _bind_tenant(cursor, tenant_id)
            with pytest.raises(Exception, match="trust_policy_append_only"):
                cursor.execute(
                    "UPDATE public.trust_tenant_policy_events SET policy_state='read_only'"
                    " WHERE tenant_id=%s",
                    (str(tenant_id),),
                )
            owner.rollback()
            _bind_tenant(cursor, tenant_id)
            with pytest.raises(Exception, match="trust_policy_append_only"):
                cursor.execute(
                    "DELETE FROM public.trust_tenant_policy_events"
                    " WHERE tenant_id=%s",
                    (str(tenant_id),),
                )
            owner.rollback()
    finally:
        owner.close()
    print("VII2_H10_POLICY_PUBLISHER_PASS")
