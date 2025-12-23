"""Manifest mapping core tables to approved builder functions."""

from __future__ import annotations

from .core_builders import (
    build_attribution_allocation,
    build_attribution_event,
    build_revenue_ledger,
    build_tenant,
)

CORE_TABLE_BUILDERS = {
    "tenants": build_tenant,
    "attribution_events": build_attribution_event,
    "attribution_allocations": build_attribution_allocation,
    "revenue_ledger": build_revenue_ledger,
}

# Tables that require tenant RLS context; used by guard tests for cleanup/selection.
TENANT_SCOPED_TABLES = {
    "tenants",
    "attribution_events",
    "attribution_allocations",
    "revenue_ledger",
}
