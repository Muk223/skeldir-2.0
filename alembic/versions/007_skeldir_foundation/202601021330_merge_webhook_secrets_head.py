"""Merge webhook secrets head into skeldir_foundation chain

Revision ID: 202601021330
Revises: de648b76dd68, 202511171000
Create Date: 2026-01-02 13:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "202601021330"
down_revision: Union[str, None] = ("de648b76dd68", "202511171000")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
