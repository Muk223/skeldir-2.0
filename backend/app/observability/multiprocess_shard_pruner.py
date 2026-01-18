"""
B0.5.6.5: Conservative pruning for prometheus_client multiprocess shard files.

Prometheus multiprocess mode stores per-PID metric shards in PROMETHEUS_MULTIPROC_DIR.
Celery child recycling and hard crashes can leave orphan shards behind. This module
provides a bounded, conservative sweeper that deletes only stale *.db shard files
for PIDs that are not in the worker parent's known-live PID set.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path


_PID_FROM_FILENAME = re.compile(r".*_(?P<pid>[0-9]+)\.db$")


@dataclass(frozen=True, slots=True)
class MultiprocPruneResult:
    scanned_db_files: int
    orphan_db_files_detected: int
    pruned_db_files: int
    shard_db_file_count: int
    overflow: bool


def _extract_pid_from_db_filename(path: Path) -> int | None:
    match = _PID_FROM_FILENAME.match(path.name)
    if not match:
        return None
    try:
        return int(match.group("pid"))
    except ValueError:
        return None


def iter_multiproc_db_files(multiproc_dir: Path) -> list[Path]:
    return list(multiproc_dir.glob("*.db"))


def prune_stale_multiproc_shards(
    *,
    multiproc_dir: Path,
    live_pids: set[int],
    grace_seconds: int,
    max_shard_files: int,
    now: float | None = None,
) -> MultiprocPruneResult:
    """
    Prune stale multiprocess metric shards.

    Contract:
    - Only files ending in *.db are candidates.
    - Only files with a PID suffix (e.g., *_123.db) are considered.
    - Only PIDs not in live_pids are eligible.
    - Only if mtime is older than grace_seconds are files deleted.
    - Non-matching files (including sentinels) are never touched.
    """
    if now is None:
        now = time.time()

    db_files = iter_multiproc_db_files(multiproc_dir)
    shard_db_file_count = len(db_files)
    overflow = shard_db_file_count > max_shard_files

    scanned = 0
    orphan_detected = 0
    pruned = 0

    for path in db_files:
        pid = _extract_pid_from_db_filename(path)
        if pid is None:
            continue
        scanned += 1
        if pid in live_pids:
            continue

        orphan_detected += 1
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue

        if (now - mtime) < grace_seconds:
            continue

        try:
            path.unlink()
        except OSError:
            continue
        pruned += 1

    return MultiprocPruneResult(
        scanned_db_files=scanned,
        orphan_db_files_detected=orphan_detected,
        pruned_db_files=pruned,
        shard_db_file_count=shard_db_file_count,
        overflow=overflow,
    )

