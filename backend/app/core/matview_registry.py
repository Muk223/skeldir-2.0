"""
Compatibility shim for legacy imports.

Authoritative registry now lives in app.matviews.registry.
"""
from typing import List

from app.matviews.registry import get_entry, list_names

MATERIALIZED_VIEWS: List[str] = list_names()


def get_all_matviews() -> List[str]:
    """
    Return canonical list of all managed materialized views.
    """
    return list_names()


def validate_matview_name(view_name: str) -> bool:
    """
    Validate that a matview name is in the canonical registry.
    """
    try:
        get_entry(view_name)
    except ValueError:
        return False
    return True
