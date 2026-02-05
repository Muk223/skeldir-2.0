"""Anchor post-merge revision for unambiguous downgrade (B0.7 P1).

Revision ID: 202602051220
Revises: c0a524bf2357
Create Date: 2026-02-05 12:20:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "202602051220"
down_revision: Union[str, None] = "c0a524bf2357"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op anchor revision to make downgrade steps unambiguous."""


def downgrade() -> None:
    """No-op anchor revision to make downgrade steps unambiguous."""
