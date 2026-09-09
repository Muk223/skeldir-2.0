"""Corrective VIII: simulation route-mount sensor (falsifier NC-P14-24).

The supported product boundary is HTTP. Exactly one non-test caller -- the
mounted POST route -- may invoke simulation admission, and exactly one
SELECT surface -- the mounted GET route -- may read it back. If the router
is unmounted in ``backend/app/main.py``, both boundaries silently vanish
while every unit-level suite stays green.

This test asserts the mount is present AND effective (not commented out),
mirroring the ``trust_api`` mount assertion in
``test_b25_p10_trust_api_surface.py``. DB-free by design: it measures
wiring, not behavior.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN = REPO_ROOT / "backend" / "app" / "main.py"
MOUNT_PREFIX = "app.include_router(trust_simulations.router"


def _effective_mount_lines() -> list[str]:
    lines = MAIN.read_text(encoding="utf-8").splitlines()
    return [
        line
        for line in lines
        if MOUNT_PREFIX in line and line.strip().startswith("app.include_router(")
    ]


def test_viii_simulation_router_is_mounted() -> None:
    assert MAIN.exists(), f"application entrypoint missing: {MAIN}"
    mounted = _effective_mount_lines()
    assert len(mounted) == 1, (
        "simulation POST/GET boundary is not mounted exactly once; "
        f"effective mount lines: {mounted}"
    )


def test_viii_simulation_router_import_is_effective() -> None:
    lines = MAIN.read_text(encoding="utf-8").splitlines()
    imported = [
        line
        for line in lines
        if "trust_simulations" in line
        and line.strip().startswith("from app.api import trust_simulations")
    ]
    assert len(imported) == 1, f"simulation router import missing: {imported}"
