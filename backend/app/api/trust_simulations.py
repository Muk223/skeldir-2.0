"""Explicit Design Partner simulation requests and tenant-safe durable reads."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select, text

from app.api.trust_api import get_machine_db_session, require_envelope_read_tenant_context
from app.bayesian.models import BayesianModelFit
from app.bayesian.source_snapshot import compute_source_snapshot_hash
from app.core.physical_authority import assert_physical_authority
from app.db.session import AsyncSessionLocal
from app.schemas.trust_simulations import SimulationSubmission
from app.simulation.contract import ChannelEvidence, SIMULATION_ADMISSIBLE_POLICY_STATES
from app.simulation.persistence import conduct_requested_simulation
from app.trust.hash_identity import compute_envelope_payload_hash
from app.trust.refusal import tenant_hash
from app.trust.runtime_keys import load_runtime_verification_registry
from app.trust.verification import verify_trust_envelope

router = APIRouter(prefix="/trust/v1/simulations")


async def _source(session, tenant_id: UUID, envelope_id: str, final_hash: str):
    result = await session.execute(text("""
        SELECT envelope_hash,final_envelope_hash,semantic_truth_hash,signed_envelope
        FROM public.trust_final_issuance_identity
        WHERE tenant_id=:tenant AND source_envelope_id=:envelope AND final_envelope_hash=:final_hash
    """), {"tenant": str(tenant_id), "envelope": envelope_id, "final_hash": final_hash})
    rows = result.mappings().all()
    if len(rows) != 1:
        raise HTTPException(404, "Source Trust unavailable")
    row = rows[0]
    envelope = row["signed_envelope"]
    if (compute_envelope_payload_hash(envelope) != row["final_envelope_hash"]
        or envelope.get("semantic_truth_hash") != row["semantic_truth_hash"]
        or verify_trust_envelope(envelope, key_registry=load_runtime_verification_registry()).verification_status != "verified"):
        raise HTTPException(409, "Source Trust identity invalid")
    if envelope["policy_action_authority"]["policy_state"] not in SIMULATION_ADMISSIBLE_POLICY_STATES:
        raise HTTPException(403, "Source policy forbids simulation")
    if datetime.fromisoformat(envelope["valid_until"].replace("Z", "+00:00")) <= datetime.now(timezone.utc):
        raise HTTPException(409, "Source Trust expired")
    return row


def derive_simulation_channels(rows) -> tuple[tuple[ChannelEvidence, ...], str]:
    """Build governed channel evidence from one fit-window measurement.

    Pure function of the measured rows so the money law is unit-falsifiable
    without a topology: mixed or missing currencies are refused, never
    silently aggregated, and integer minor units are preserved end to end.
    """
    currencies = {row[3] for row in rows}
    if len(currencies) != 1 or None in currencies:
        raise HTTPException(422, "Single-currency evidence required")
    channels = tuple(
        ChannelEvidence(str(row[0]), int(row[1]), int(row[2])) for row in rows
    )
    return channels, currencies.pop()


def _presented_token(request: Request) -> str:
    """Re-present the already-authenticated machine credential for the
    possession proof. The authentication dependency guarantees a valid
    Bearer credential reached this handler; this re-extraction never
    invents one."""
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Simulation credential required")
    return token


async def _evidence(session, *, tenant_id: UUID, envelope: dict):
    if envelope["subject_type"] != "confidence_projection":
        raise HTTPException(422, "Simulation requires fit-scoped confidence Trust")
    fit_id = UUID(envelope["subject_ref"].rsplit(":", 1)[1])
    fit = (await session.execute(select(BayesianModelFit).where(
        BayesianModelFit.tenant_id == tenant_id, BayesianModelFit.id == fit_id
    ))).scalar_one_or_none()
    if fit is None or fit.status != "succeeded":
        raise HTTPException(409, "Source fit unavailable")

    async def channels_in_snapshot(snapshot_session):
        # Allocations have no ORM model. This joins the governed conversion
        # relation in the same MVCC snapshot whose hash is compared below.
        result = await snapshot_session.execute(text("""
            SELECT a.channel_code, sum(a.allocated_revenue_cents)::bigint,
                   count(DISTINCT a.event_id)::int, upper(e.currency)
            FROM public.attribution_allocations a
            JOIN public.attribution_events e ON e.id=a.event_id AND e.tenant_id=a.tenant_id
            WHERE a.tenant_id=:tenant AND a.verified=true
              AND e.occurred_at>=:start AND e.occurred_at<:end
              AND e.event_type IN ('purchase','conversion')
            GROUP BY a.channel_code,upper(e.currency)
            HAVING sum(a.allocated_revenue_cents)>0
            ORDER BY a.channel_code
        """), {"tenant": str(tenant_id), "start": fit.source_window_start, "end": fit.source_window_end})
        return result.fetchall()

    async with AsyncSessionLocal() as snapshot_session:
        snapshot = await compute_source_snapshot_hash(
            snapshot_session, tenant_id=tenant_id, model_type=fit.model_type,
            model_version=fit.model_version, source_window_start=fit.source_window_start,
            source_window_end=fit.source_window_end, within_snapshot=channels_in_snapshot,
        )
    if "sha256:" + snapshot.source_snapshot_hash != envelope["truth_authority"]["source_snapshot_hash"]:
        raise HTTPException(409, "Source evidence changed; request a fresh Trust")
    rows = snapshot.within_snapshot_result
    return derive_simulation_channels(rows)


@router.post("", status_code=201, operation_id="requestTrustSimulation")
async def request_simulation(
    submission: SimulationSubmission, request: Request,
    correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")],
    caller=Depends(require_envelope_read_tenant_context),
    session=Depends(get_machine_db_session),
):
    """Authenticate, resolve exact issuance and persist one explicit request."""
    await assert_physical_authority(session)
    source = await _source(session, caller.tenant_id, submission.source_envelope_id, submission.source_final_envelope_hash)
    channels, currency = await _evidence(session, tenant_id=caller.tenant_id, envelope=source["signed_envelope"])
    try:
        outcome = await asyncio.to_thread(
            conduct_requested_simulation, envelope=source["signed_envelope"],
            tenant_id=str(caller.tenant_id), presented_token=_presented_token(request),
            source_issuance_envelope_hash=source["envelope_hash"],
            total_budget_minor=submission.total_budget_minor, currency=currency,
            channels=channels, request_ref=submission.request_ref,
        )
    except Exception as exc:
        reason = str(exc)
        code = 403 if "policy_forbids" in reason else 409
        raise HTTPException(code, "Simulation request refused") from exc
    return {"request_id": outcome["request_id"], "tenant_id_hash": tenant_hash(caller.tenant_id),
            "correlation_id": str(correlation_id), "status": "completed" if outcome["identifiers"].get("persisted") == "true" else "refused"}


@router.get("/{request_id}", operation_id="readTrustSimulation")
async def read_simulation(
    request_id: UUID, correlation_id: Annotated[UUID, Header(alias="X-Correlation-ID")],
    caller=Depends(require_envelope_read_tenant_context), session=Depends(get_machine_db_session),
):
    """Read conserved durable fields; foreign identifiers reveal no artifact."""
    await assert_physical_authority(session)
    result = await session.execute(text("""
        SELECT q.id,q.source_envelope_id,q.source_semantic_truth_hash,q.input_snapshot_hash,
               q.total_budget_minor,q.currency,q.requested_at,q.sufficiency_verdict,
               r.solver_consequence_kind,r.allocations,r.action_authority,
               p.proposal_ref,p.requires_human_approval
        FROM public.b28_simulation_requests q
        LEFT JOIN public.b28_simulation_results r ON r.tenant_id=q.tenant_id AND r.request_id=q.id
        LEFT JOIN public.b28_proposals p ON p.tenant_id=r.tenant_id AND p.result_id=r.id
        WHERE q.tenant_id=:tenant AND q.id=:request
    """), {"tenant": str(caller.tenant_id), "request": str(request_id)})
    row = result.mappings().first()
    if row is None:
        raise HTTPException(404, "Simulation unavailable")
    return {**dict(row), "tenant_id_hash": tenant_hash(caller.tenant_id), "correlation_id": str(correlation_id),
            "status": "completed" if row["proposal_ref"] else "pending" if row["sufficiency_verdict"] else "refused",
            "causal_authority": "none", "external_execution_authority": "none"}
