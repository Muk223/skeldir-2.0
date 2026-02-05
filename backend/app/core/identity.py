"""
Identity helpers for user-scoped contexts.

Defines a deterministic fallback user_id for system-initiated operations where
no authenticated user context is available.
"""

from __future__ import annotations

from uuid import UUID


SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


def resolve_user_id(value: UUID | str | None) -> UUID:
    """
    Normalize user_id inputs to a UUID.

    Falls back to SYSTEM_USER_ID when input is missing or invalid.
    """
    if value is None:
        return SYSTEM_USER_ID
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return SYSTEM_USER_ID
