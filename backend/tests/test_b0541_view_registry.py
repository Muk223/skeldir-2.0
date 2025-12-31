import json
import logging
import os

import pytest

from app.matviews import registry
from app.tasks import maintenance

logger = logging.getLogger(__name__)


def _run_sha() -> str:
    return os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA") or "local"


def _emit_gate(marker: str, payload: dict) -> None:
    payload_with_sha = {"sha": _run_sha(), **payload}
    logger.info(
        "EG_B0541_%s_BEGIN %s EG_B0541_%s_END",
        marker,
        json.dumps(payload_with_sha, separators=(",", ":"), sort_keys=True),
        marker,
    )


def test_b0541_gate_1a_closed_set():
    expected = [
        "mv_allocation_summary",
        "mv_channel_performance",
        "mv_daily_revenue_summary",
        "mv_realtime_revenue",
        "mv_reconciliation_status",
    ]
    actual = registry.list_names()
    _emit_gate("G1A", {"registry_names": actual})
    assert sorted(actual) == sorted(expected)


def test_b0541_gate_1b_metadata_completeness():
    entries = registry.list_entries()
    serialized = []
    for entry in entries:
        serialized.append(
            {
                "name": entry.name,
                "kind": entry.kind,
                "has_refresh_sql": bool(entry.refresh_sql),
                "has_refresh_fn": bool(entry.refresh_fn),
                "dependencies": list(entry.dependencies),
                "max_staleness_seconds": entry.max_staleness_seconds,
                "schedule_class": entry.schedule_class,
            }
        )
        assert entry.name
        assert entry.kind
        assert entry.dependencies is not None
        assert entry.max_staleness_seconds is not None
        assert entry.schedule_class in {
            registry.SCHEDULE_CLASS_REALTIME,
            registry.SCHEDULE_CLASS_MINUTE,
            registry.SCHEDULE_CLASS_HOURLY,
        }
        assert entry.refresh_sql or entry.refresh_fn
    _emit_gate("G1B", {"entries": serialized})


def test_b0541_gate_1c_anti_injection():
    valid_name = "mv_allocation_summary"
    invalid_names = [
        "pg_class",
        "mv_realtime_revenue;DROP TABLE worker_failed_jobs;--",
        "public.mv_realtime_revenue",
        "mv_realtime_revenue;select 1",
    ]

    entry = registry.get_entry(valid_name)
    qualified = maintenance._qualified_matview_identifier(valid_name, task_id="t", tenant_id=None)

    invalid_failures = []
    for name in invalid_names:
        with pytest.raises(ValueError):
            registry.get_entry(name)
        with pytest.raises(ValueError):
            maintenance._validated_matview_identifier(name, task_id="t", tenant_id=None)
        invalid_failures.append(name)

    _emit_gate(
        "G1C",
        {
            "valid_name": valid_name,
            "qualified_identifier": qualified,
            "invalid_names": invalid_failures,
            "entry_kind": entry.kind,
        },
    )
