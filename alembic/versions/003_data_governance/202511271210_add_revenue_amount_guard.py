"""Add amount_cents >= 0 guardrail to revenue_ledger

Revision ID: 202511271210
Revises: 202511171530
Create Date: 2025-11-27 12:10:00.000000

This migration enforces the canonical schema requirement that revenue_ledger.amount_cents
must be non-negative by adding a CHECK constraint.
"""

from alembic import op
from typing import Union


# revision identifiers, used by Alembic.
revision: str = '202511271210'
down_revision: Union[str, None] = '202511171530'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'ck_revenue_ledger_amount_positive'
                  AND conrelid = 'public.revenue_ledger'::regclass
            ) THEN
                ALTER TABLE public.revenue_ledger
                ADD CONSTRAINT ck_revenue_ledger_amount_positive
                CHECK (amount_cents >= 0);
            END IF;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'ck_revenue_ledger_amount_positive'
                  AND conrelid = 'public.revenue_ledger'::regclass
            ) THEN
                ALTER TABLE public.revenue_ledger
                DROP CONSTRAINT ck_revenue_ledger_amount_positive;
            END IF;
        END;
        $$;
        """
    )

