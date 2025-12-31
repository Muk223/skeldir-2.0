"""
Authoritative registry of refreshable materialized views.

Closed set: only entries defined here are refreshable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Sequence

KIND_MATERIALIZED_VIEW = "materialized_view"

SCHEDULE_CLASS_REALTIME = "realtime"
SCHEDULE_CLASS_MINUTE = "minute"
SCHEDULE_CLASS_HOURLY = "hourly"

REFRESH_SQL_CONCURRENTLY = "REFRESH MATERIALIZED VIEW CONCURRENTLY {qualified_name}"


@dataclass(frozen=True)
class MatviewRegistryEntry:
    name: str
    kind: str
    refresh_sql: Optional[str]
    refresh_fn: Optional[Callable[..., object]]
    dependencies: Sequence[str]
    max_staleness_seconds: int
    schedule_class: str
    schedule_source: str


_REGISTRY: dict[str, MatviewRegistryEntry] = {
    "mv_allocation_summary": MatviewRegistryEntry(
        name="mv_allocation_summary",
        kind=KIND_MATERIALIZED_VIEW,
        refresh_sql=REFRESH_SQL_CONCURRENTLY,
        refresh_fn=None,
        dependencies=(),
        max_staleness_seconds=60,
        schedule_class=SCHEDULE_CLASS_REALTIME,
        schedule_source="alembic/versions/003_data_governance/202511161110_fix_mv_allocation_summary_left_join.py:93-96",
    ),
    "mv_channel_performance": MatviewRegistryEntry(
        name="mv_channel_performance",
        kind=KIND_MATERIALIZED_VIEW,
        refresh_sql=REFRESH_SQL_CONCURRENTLY,
        refresh_fn=None,
        dependencies=(),
        max_staleness_seconds=3600,
        schedule_class=SCHEDULE_CLASS_HOURLY,
        schedule_source="alembic/versions/003_data_governance/202511151500_add_mv_channel_performance.py:101",
    ),
    "mv_daily_revenue_summary": MatviewRegistryEntry(
        name="mv_daily_revenue_summary",
        kind=KIND_MATERIALIZED_VIEW,
        refresh_sql=REFRESH_SQL_CONCURRENTLY,
        refresh_fn=None,
        dependencies=(),
        max_staleness_seconds=3600,
        schedule_class=SCHEDULE_CLASS_HOURLY,
        schedule_source="alembic/versions/003_data_governance/202511151510_add_mv_daily_revenue_summary.py:103",
    ),
    "mv_realtime_revenue": MatviewRegistryEntry(
        name="mv_realtime_revenue",
        kind=KIND_MATERIALIZED_VIEW,
        refresh_sql=REFRESH_SQL_CONCURRENTLY,
        refresh_fn=None,
        dependencies=(),
        max_staleness_seconds=60,
        schedule_class=SCHEDULE_CLASS_REALTIME,
        schedule_source="alembic/versions/001_core_schema/202511131119_add_materialized_views.py:63",
    ),
    "mv_reconciliation_status": MatviewRegistryEntry(
        name="mv_reconciliation_status",
        kind=KIND_MATERIALIZED_VIEW,
        refresh_sql=REFRESH_SQL_CONCURRENTLY,
        refresh_fn=None,
        dependencies=(),
        max_staleness_seconds=60,
        schedule_class=SCHEDULE_CLASS_REALTIME,
        schedule_source="alembic/versions/001_core_schema/202511131119_add_materialized_views.py:90",
    ),
}


def get_entry(view_name: str) -> MatviewRegistryEntry:
    """
    Return registry entry for view_name or raise ValueError.
    """
    entry = _REGISTRY.get(view_name)
    if entry is None:
        raise ValueError(f"View '{view_name}' not in registry")
    return entry


def list_entries() -> list[MatviewRegistryEntry]:
    """
    Return registry entries in deterministic order.
    """
    return [*_REGISTRY.values()]


def list_names() -> list[str]:
    """
    Return registry names in deterministic order.
    """
    return list(_REGISTRY.keys())


def all_entries() -> Iterable[MatviewRegistryEntry]:
    """
    Iterator over registry entries.
    """
    return _REGISTRY.values()
