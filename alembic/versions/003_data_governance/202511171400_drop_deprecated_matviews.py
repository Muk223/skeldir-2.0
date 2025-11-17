"""Drop deprecated materialized views

Revision ID: 202511171400
Revises: 202511171300
Create Date: 2025-11-17 14:00:00.000000

Phase 6 of B0.3 Functional Implementation Plan

This migration drops the deprecated materialized views that reference non-existent columns:
- mv_realtime_revenue (uses revenue_cents, is_verified - columns don't exist)
- mv_reconciliation_status (superseded by canonical views)

These views are replaced by:
- mv_channel_performance (for channel analytics)
- mv_daily_revenue_summary (for revenue analytics)

Sunset timeline: 30 days after Phase 6 completion (allows API migration window).

Exit Gates:
- Migration applies cleanly
- Deprecated views removed
- No dependent objects remain
"""

from alembic import op
import sqlalchemy as sa
from typing import Union


# revision identifiers, used by Alembic.
revision: str = '202511171400'
down_revision: Union[str, None] = '202511171300'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """
    Drop deprecated materialized views.
    
    Implementation:
    1. Drop mv_realtime_revenue (CASCADE to remove indexes)
    2. Drop mv_reconciliation_status (CASCADE to remove indexes)
    """
    
    # Drop deprecated views with CASCADE to remove associated indexes
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_realtime_revenue CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_reconciliation_status CASCADE")


def downgrade() -> None:
    """
    Recreate deprecated materialized views (for rollback only).
    
    WARNING: These views reference non-existent columns and will fail to refresh.
    This downgrade is provided for migration safety but should not be used in production.
    """
    
    # Recreate mv_realtime_revenue (will fail if columns don't exist)
    op.execute("""
        CREATE MATERIALIZED VIEW mv_realtime_revenue AS
        SELECT 
            rl.tenant_id,
            COALESCE(SUM(rl.revenue_cents), 0) / 100.0 AS total_revenue,
            BOOL_OR(rl.is_verified) AS verified,
            EXTRACT(EPOCH FROM (now() - MAX(rl.updated_at)))::INTEGER AS data_freshness_seconds
        FROM revenue_ledger rl
        GROUP BY rl.tenant_id
    """)
    
    op.execute("""
        CREATE UNIQUE INDEX idx_mv_realtime_revenue_tenant_id 
        ON mv_realtime_revenue (tenant_id)
    """)
    
    # Recreate mv_reconciliation_status
    op.execute("""
        CREATE MATERIALIZED VIEW mv_reconciliation_status AS
        SELECT 
            rr.tenant_id,
            rr.state,
            rr.last_run_at,
            rr.id AS reconciliation_run_id
        FROM reconciliation_runs rr
        INNER JOIN (
            SELECT tenant_id, MAX(last_run_at) AS max_last_run_at
            FROM reconciliation_runs
            GROUP BY tenant_id
        ) latest ON rr.tenant_id = latest.tenant_id 
            AND rr.last_run_at = latest.max_last_run_at
    """)
    
    op.execute("""
        CREATE UNIQUE INDEX idx_mv_reconciliation_status_tenant_id 
        ON mv_reconciliation_status (tenant_id)
    """)

