"""B0.3 reconciliation: canonical index + remediation constraint alignment.

Revision ID: 202511171200
Revises: 202511161130
Create Date: 2025-11-17 12:00:00

Purpose:
- Ensure the canonical OLAP index `idx_allocations_channel_performance` exists with the
  expected `(tenant_id, channel_code, created_at DESC)` key structure and INCLUDE payload.
- Align `dead_events.remediation_status` CHECK constraint with canonical values
  (`pending`, `in_progress`, `resolved`, `abandoned`) instead of the legacy `'ignored'`.

Exit Gates:
- `\dx`
- (1) `\d+ attribution_allocations` shows the composite index with INCLUDE columns.
- (2) Inserting `dead_events` rows outside canonical enum values fails; canonical list succeeds.
"""

from typing import Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "202511171200"
down_revision: Union[str, None] = "202511161130"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create canonical allocation index and enforce remediation enum."""

    # Rebuild canonical composite index (drop if partial/legacy definition exists).
    op.execute(
        """
        DROP INDEX IF EXISTS idx_allocations_channel_performance;
        """
    )
    op.execute(
        """
        CREATE INDEX idx_allocations_channel_performance
        ON attribution_allocations (tenant_id, channel_code, created_at DESC)
        INCLUDE (allocated_revenue_cents, confidence_score);
        """
    )

    # Align remediation_status CHECK constraint with canonical enum.
    op.execute(
        """
        ALTER TABLE dead_events
        DROP CONSTRAINT IF EXISTS ck_dead_events_remediation_status_valid;
        """
    )
    op.execute(
        """
        ALTER TABLE dead_events
        ADD CONSTRAINT ck_dead_events_remediation_status_valid
        CHECK (remediation_status IN ('pending', 'in_progress', 'resolved', 'abandoned'));
        """
    )


def downgrade() -> None:
    """Rollback to pre-reconciliation state."""

    op.execute(
        """
        DROP INDEX IF EXISTS idx_allocations_channel_performance;
        """
    )

    op.execute(
        """
        ALTER TABLE dead_events
        DROP CONSTRAINT IF EXISTS ck_dead_events_remediation_status_valid;
        """
    )
    op.execute(
        """
        ALTER TABLE dead_events
        ADD CONSTRAINT ck_dead_events_remediation_status_valid
        CHECK (remediation_status IN ('pending', 'in_progress', 'resolved', 'ignored'));
        """
    )

