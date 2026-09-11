"""B2.6-P1 positive coverage-origin admission seam (authority infrastructure).

P1 remains authority/proof-plane only. This module creates no reconciliation
state, table, API, worker, scheduler, export, or TrustEnvelope field. It
states positively which producer may create canonical verification-coverage
authority and refuses every other origin regardless of numeric coincidence
or transport.

Canonical law
-------------

``CANONICAL_COVERAGE(value)`` holds only when ``SOURCE(value)`` is the
sovereign B2.3 verification-coverage authority under the governed
tenant/currency/window/provider scope. A plain number, an independently
computed ratio, a legacy-service response, an estimation/counterfactual
blend, or an explanation-model output can never satisfy this law, even when
its digits equal the sovereign result.

Mechanism
---------

The sovereign B2.3 callable pair
``fetch_verification_coverage_aggregate`` + ``VERIFICATION_COVERAGE.compute``
is the only producer. :func:`load_canonical_verification_coverage` invokes
that pair and wraps the outcome in :class:`CanonicalVerificationCoverage`
with a module-private seal. :func:`admit_canonical_verification_coverage`
accepts only sealed instances whose producer identity and internal
aggregate/result correspondence verify. Direct construction outside this
module yields an unsealed instance that admission refuses, so provenance
cannot be forged by calling the constructor. Serialized diagnostic copies
likewise carry no seal and are refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Mapping, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:  # Import-time light: sovereign modules load only on use.
    from app.revenue_verification.verification_coverage import (
        VerificationCoverageAggregate,
        VerificationCoverageResult,
    )


def _sovereign():
    """Load the sovereign B2.3 coverage modules on use, not on import."""
    from app.revenue_verification import (  # noqa: PLC0415
        verification_coverage as sovereign,
    )

    return sovereign


B23_SOVEREIGN_COVERAGE_PRODUCER = (
    "app.revenue_verification.verification_coverage."
    "fetch_verification_coverage_aggregate"
    "+app.revenue_verification.verification_coverage."
    "VERIFICATION_COVERAGE.compute"
)
CANONICAL_COVERAGE_LAW = "only_sealed_B2.3_origin_may_be_canonical"
CANONICAL_ADMISSION_MODULE = "app.finance_reconciliation.coverage_authority"
CANONICAL_SEALED_TYPE = (
    "app.finance_reconciliation.coverage_authority.CanonicalVerificationCoverage"
)
CANONICAL_LOADER = (
    "app.finance_reconciliation.coverage_authority."
    "load_canonical_verification_coverage"
)
CANONICAL_ADMITTER = (
    "app.finance_reconciliation.coverage_authority."
    "admit_canonical_verification_coverage"
)
CANONICAL_SCOPE_VERIFIER = (
    "app.finance_reconciliation.coverage_authority.require_canonical_scope"
)


class CanonicalCoverageAuthorityError(ValueError):
    """A value claimed as canonical coverage lacks sovereign B2.3 origin."""


@dataclass(frozen=True)
class CanonicalVerificationCoverage:
    """Sealed canonical verification-coverage value.

    Only :func:`load_canonical_verification_coverage` in this module can
    produce a sealed instance. Every other construction path yields
    ``_sealed is False`` and is refused by
    :func:`admit_canonical_verification_coverage`.
    """

    aggregate: VerificationCoverageAggregate
    result: VerificationCoverageResult
    producer: str
    supported_platforms: tuple[str, ...]
    _sealed: bool = field(default=False, repr=False, compare=False)


def _supported_platform_universe() -> frozenset[str]:
    return frozenset(_sovereign().SUPPORTED_VERIFICATION_COVERAGE_PLATFORMS)


def _supported_currency_universe() -> frozenset[str]:
    return frozenset(_sovereign().SUPPORTED_VERIFICATION_COVERAGE_CURRENCIES)


def _normalize_platforms(
    supported_platforms: Sequence[str] | None,
) -> tuple[str, ...]:
    if supported_platforms is None:
        return tuple(sorted(_supported_platform_universe()))
    normalized = tuple(sorted({str(item).strip().lower() for item in supported_platforms if str(item).strip()}))
    if not normalized:
        raise CanonicalCoverageAuthorityError(
            "canonical_coverage_supported_platforms_required"
        )
    unsupported = set(normalized) - set(_supported_platform_universe())
    if unsupported:
        raise CanonicalCoverageAuthorityError(
            f"canonical_coverage_unsupported_platform:{sorted(unsupported)}"
        )
    return normalized


def _check_internal_correspondence(value: CanonicalVerificationCoverage) -> None:
    sovereign = _sovereign()
    aggregate = value.aggregate
    result = value.result
    if not isinstance(aggregate, sovereign.VerificationCoverageAggregate):
        raise CanonicalCoverageAuthorityError(
            "canonical_coverage_aggregate_not_sovereign_type"
        )
    if not isinstance(result, sovereign.VerificationCoverageResult):
        raise CanonicalCoverageAuthorityError(
            "canonical_coverage_result_not_sovereign_type"
        )
    if (
        aggregate.tenant_id != result.tenant_id
        or aggregate.currency_code != result.currency_code
        or aggregate.window_start != result.window_start
        or aggregate.window_end != result.window_end
        or aggregate.matched_webhook_revenue_minor
        != result.numerator_matched_webhook_revenue_minor
        or aggregate.connected_platform_revenue_minor
        != result.denominator_connected_platform_revenue_minor
    ):
        raise CanonicalCoverageAuthorityError(
            "canonical_coverage_aggregate_result_scope_mismatch"
        )


def _seal(
    aggregate: VerificationCoverageAggregate,
    result: VerificationCoverageResult,
    supported_platforms: tuple[str, ...],
) -> CanonicalVerificationCoverage:
    value = CanonicalVerificationCoverage(
        aggregate=aggregate,
        result=result,
        producer=B23_SOVEREIGN_COVERAGE_PRODUCER,
        supported_platforms=tuple(supported_platforms),
    )
    object.__setattr__(value, "_sealed", True)
    return value


async def load_canonical_verification_coverage(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    window_start: datetime,
    window_end: datetime,
    supported_platforms: Sequence[str] | None = None,
    currency_code: str = "USD",
) -> CanonicalVerificationCoverage:
    """Load canonical coverage through the sovereign B2.3 producer only."""
    sovereign = _sovereign()
    platforms = _normalize_platforms(supported_platforms)
    aggregate = await sovereign.fetch_verification_coverage_aggregate(
        session,
        tenant_id=tenant_id,
        window_start=window_start,
        window_end=window_end,
        supported_platforms=platforms,
        currency_code=currency_code,
    )
    result = sovereign.VERIFICATION_COVERAGE.compute(aggregate)
    sealed = _seal(aggregate, result, platforms)
    return admit_canonical_verification_coverage(sealed)


def admit_canonical_verification_coverage(
    candidate: Any,
) -> CanonicalVerificationCoverage:
    """Admit a value as canonical coverage or refuse it.

    Refuses plain numbers, independently computed ratios, legacy-service
    payloads, estimation/counterfactual blends, explanation-model output,
    forged sealed-type constructions, and scope-incoherent pairs.
    """
    if not isinstance(candidate, CanonicalVerificationCoverage):
        raise CanonicalCoverageAuthorityError(
            f"canonical_coverage_origin_not_sovereign:{type(candidate).__name__}"
        )
    if candidate.producer != B23_SOVEREIGN_COVERAGE_PRODUCER:
        raise CanonicalCoverageAuthorityError(
            f"canonical_coverage_producer_not_sovereign:{candidate.producer}"
        )
    if candidate._sealed is not True:
        raise CanonicalCoverageAuthorityError(
            "canonical_coverage_unsealed_forged_construction"
        )
    _check_internal_correspondence(candidate)
    return candidate


def require_canonical_scope(
    coverage: CanonicalVerificationCoverage,
    *,
    tenant_id: UUID,
    currency_code: str,
    window_start: datetime,
    window_end: datetime,
    supported_platforms: Sequence[str] | None = None,
) -> CanonicalVerificationCoverage:
    """Require governed scope identity on an admitted canonical value."""
    admitted = admit_canonical_verification_coverage(coverage)
    platforms = _normalize_platforms(supported_platforms)
    aggregate = admitted.aggregate
    if (
        aggregate.tenant_id != tenant_id
        or aggregate.currency_code != str(currency_code).strip().upper()
        or aggregate.window_start != window_start
        or aggregate.window_end != window_end
        or tuple(admitted.supported_platforms) != platforms
    ):
        raise CanonicalCoverageAuthorityError(
            "canonical_coverage_scope_identity_mismatch"
        )
    if aggregate.currency_code not in _supported_currency_universe():
        raise CanonicalCoverageAuthorityError(
            "canonical_coverage_currency_not_governed"
        )
    return admitted


def to_diagnostic_dict(coverage: CanonicalVerificationCoverage) -> Mapping[str, Any]:
    """Render an explicitly non-authoritative diagnostic copy.

    The copy carries no seal. Feeding it back to
    :func:`admit_canonical_verification_coverage` is refused by construction,
    so diagnostic display can never be mistaken for canonical authority.
    """
    admitted = admit_canonical_verification_coverage(coverage)
    aggregate = admitted.aggregate
    result = admitted.result
    return {
        "authority": "non_authoritative_diagnostic_copy",
        "producer": admitted.producer,
        "tenant_id": str(aggregate.tenant_id),
        "currency_code": aggregate.currency_code,
        "window_start": aggregate.window_start.isoformat(),
        "window_end": aggregate.window_end.isoformat(),
        "supported_platforms": list(admitted.supported_platforms),
        "matched_webhook_revenue_minor": aggregate.matched_webhook_revenue_minor,
        "connected_platform_revenue_minor": aggregate.connected_platform_revenue_minor,
        "coverage_percent": str(result.coverage_percent),
    }
