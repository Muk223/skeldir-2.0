"""B2.5-P14 Corrective VII-2 unit proofs: money and credential boundaries.

No database. H-VII2-05 (mixed-currency evidence can never silently combine)
and the request-credential re-presentation rule are properties of pure
functions, so they are proved here rather than through a topology.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.trust_simulations import derive_simulation_channels


def _row(channel: str, revenue: int, conversions: int, currency):
    return (channel, revenue, conversions, currency)


def test_vii2_single_currency_evidence_is_preserved_exactly() -> None:
    channels, currency = derive_simulation_channels(
        [
            _row("google_ads", 400_000, 12, "USD"),
            _row("meta_ads", 250_000, 7, "USD"),
        ]
    )
    assert currency == "USD"
    assert [(c.channel_id, c.verified_revenue_minor, c.conversion_count)
            for c in channels] == [
        ("google_ads", 400_000, 12),
        ("meta_ads", 250_000, 7),
    ]
    assert all(isinstance(c.verified_revenue_minor, int) for c in channels)
    print("VII2_H05_SINGLE_CURRENCY_PASS")


def test_vii2_mixed_currency_evidence_is_refused_not_combined() -> None:
    with pytest.raises(HTTPException) as exc:
        derive_simulation_channels(
            [
                _row("google_ads", 400_000, 12, "USD"),
                _row("meta_ads", 250_000, 7, "EUR"),
            ]
        )
    assert exc.value.status_code == 422
    print("VII2_H05_MIXED_CURRENCY_REFUSED_PASS")


def test_vii2_missing_currency_is_refused() -> None:
    with pytest.raises(HTTPException) as exc:
        derive_simulation_channels(
            [
                _row("google_ads", 400_000, 12, "USD"),
                _row("meta_ads", 250_000, 7, None),
            ]
        )
    assert exc.value.status_code == 422
    print("VII2_H05_MISSING_CURRENCY_REFUSED_PASS")


def test_vii2_presented_token_requires_bearer_credential() -> None:
    from app.api.trust_simulations import _presented_token

    class _Headers(dict):
        pass

    class _Request:
        def __init__(self, authorization: str | None) -> None:
            self.headers = (
                {} if authorization is None else {"Authorization": authorization}
            )

    assert (
        _presented_token(_Request("Bearer secret-token-value")) == "secret-token-value"
    )
    for bad in (None, "", "Bearer ", "Basic abc123", "Token xyz"):
        with pytest.raises(HTTPException) as exc:
            _presented_token(_Request(bad))
        assert exc.value.status_code == 401
    print("VII2_H11_CREDENTIAL_BOUNDARY_PASS")
