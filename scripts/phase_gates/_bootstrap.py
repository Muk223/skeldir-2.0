"""
Environment-invariant sys.path bootstrap for phase gate runners.

This module ensures gate runners can import both:
- scripts.phase_gates.* (repo root)
- app.* (backend/)

Regardless of PYTHONPATH configuration or working directory.

Usage:
    from scripts.phase_gates._bootstrap import bootstrap
    bootstrap()
"""

import sys
from pathlib import Path


def bootstrap() -> None:
    """
    Add repo root and backend/ to sys.path if not already present.

    This makes gate runners environment-invariant:
    - Resolves scripts.phase_gates imports
    - Resolves app.* imports
    - Works in CI, local dev, and anywhere else
    """
    # Compute paths relative to this file
    # _bootstrap.py is at: scripts/phase_gates/_bootstrap.py
    # Repo root is 2 levels up
    repo_root = Path(__file__).resolve().parents[2]
    backend_root = repo_root / "backend"

    # Add repo root to sys.path (for scripts.phase_gates imports)
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
        print(f"[Bootstrap] Added repo root to sys.path: {repo_root_str}")

    # Add backend/ to sys.path (for app.* imports)
    backend_root_str = str(backend_root)
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)
        print(f"[Bootstrap] Added backend to sys.path: {backend_root_str}")

    # Verify imports work
    try:
        import scripts.phase_gates  # noqa: F401
        print("[Bootstrap] ✓ scripts.phase_gates import verified")
    except ImportError as e:
        print(f"[Bootstrap] ✗ scripts.phase_gates import failed: {e}")
        raise

    try:
        import app  # noqa: F401
        print("[Bootstrap] ✓ app import verified")
    except ImportError as e:
        print(f"[Bootstrap] ✗ app import failed: {e}")
        raise


if __name__ == "__main__":
    bootstrap()
    print("[Bootstrap] SUCCESS: Environment-invariant paths configured")
