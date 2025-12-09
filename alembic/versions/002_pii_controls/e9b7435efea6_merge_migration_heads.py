"""merge_migration_heads

Revision ID: e9b7435efea6
Revises: 202511161210, 202512081510
Create Date: 2025-12-09 10:23:04.375727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9b7435efea6'
down_revision: Union[str, None] = ('202511161210', '202512081510')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass








