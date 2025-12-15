"""Create attribution_recompute_jobs table for window-scoped idempotency

Revision ID: 202512151300
Revises: 202512151200
Create Date: 2025-12-15 13:00:00

Migration Description:
Creates attribution_recompute_jobs table to enforce window-scoped idempotency
per B0.5.3.2 requirements. This table tracks recompute job execution identity
at the window boundary level (tenant_id, window_start, window_end, model_version)
to prevent duplicate derived outputs when rerunning the same attribution window.

Key Features:
- UNIQUE constraint on (tenant_id, window_start, window_end, model_version) -
  prevents duplicate job identity rows and enforces window-scoped idempotency
- Status tracking (pending|running|succeeded|failed) for operational visibility
- run_count for observability (how many times this window was recomputed)
- RLS enablement for tenant isolation
- Timestamps for audit trail and SLA monitoring

Contract Mapping:
- Supports B0.5.3 recompute_window task signature (tenant_id, window_start, window_end)
- Enforces "same window" identity as a provable constraint, not just a convention
- Aligns with existing "overwrite" idempotency paradigm (event-scoped → window-scoped)

Failure Mode Prevention:
- Prevents "Window Re-Run Produces Duplicates" failure mode flagged in Landscape Report
- Ensures deterministic recompute: same window → identical derived outputs
- Job tracking enables short-circuit or overwrite semantics (both are safe with this schema)

RLS Policy:
- Tenant isolation via app.current_tenant_id GUC (consistent with other attribution tables)
- Only jobs for the current tenant are visible/writable
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '202512151300'
down_revision: Union[str, None] = '202512151200'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply migration changes.

    Creates:
    1. attribution_recompute_jobs table with window identity columns
    2. UNIQUE constraint on (tenant_id, window_start, window_end, model_version)
    3. Indexes for performance (status, created_at)
    4. RLS policy for tenant isolation
    5. Grants for app_user role
    """

    # Create attribution_recompute_jobs table
    op.execute("""
        CREATE TABLE attribution_recompute_jobs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            window_start timestamptz NOT NULL,
            window_end timestamptz NOT NULL,
            model_version text NOT NULL DEFAULT '1.0.0',
            status text NOT NULL DEFAULT 'pending',
            run_count integer NOT NULL DEFAULT 0,
            last_correlation_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            started_at timestamptz,
            finished_at timestamptz
        )
    """)

    op.execute("""
        COMMENT ON TABLE attribution_recompute_jobs IS
            'Tracks attribution recompute job execution at window boundary level. Purpose: Enforce window-scoped idempotency to prevent duplicate derived outputs when rerunning the same attribution window. Data class: Non-PII. Ownership: Attribution service. RLS enabled for tenant isolation.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.id IS
            'Primary key UUID. Purpose: Unique job identifier. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.tenant_id IS
            'Tenant identifier. Purpose: Multi-tenant isolation. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.window_start IS
            'Attribution window start boundary (inclusive). Purpose: Window identity component - defines temporal scope of recompute job. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.window_end IS
            'Attribution window end boundary (exclusive). Purpose: Window identity component - defines temporal scope of recompute job. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.model_version IS
            'Attribution model version (semantic version string). Purpose: Window identity component - different model versions can have different outputs for same window. Enables model A/B testing and safe rollouts. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.status IS
            'Job execution status. Purpose: Operational visibility and workflow management. Valid values: pending, running, succeeded, failed. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.run_count IS
            'Number of times this window was recomputed. Purpose: Observability metric - indicates rerun frequency (should be low in steady state). Monotonically increasing. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.last_correlation_id IS
            'Correlation ID from most recent execution. Purpose: Distributed tracing and debugging. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.created_at IS
            'Record creation timestamp. Purpose: Audit trail - when this window identity was first scheduled. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.updated_at IS
            'Record update timestamp. Purpose: Audit trail - when this job last changed state. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.started_at IS
            'Job execution start timestamp. Purpose: SLA monitoring - when the job actually began processing. NULL if never started. Data class: Non-PII.'
    """)

    op.execute("""
        COMMENT ON COLUMN attribution_recompute_jobs.finished_at IS
            'Job execution finish timestamp. Purpose: SLA monitoring - when the job completed (success or failure). NULL if still running or never started. Data class: Non-PII.'
    """)

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE attribution_recompute_jobs
            ADD CONSTRAINT ck_attribution_recompute_jobs_status_valid
            CHECK (status IN ('pending', 'running', 'succeeded', 'failed'))
    """)

    op.execute("""
        COMMENT ON CONSTRAINT ck_attribution_recompute_jobs_status_valid ON attribution_recompute_jobs IS
            'Validates status enum. Purpose: Enforce valid status transitions and prevent typos. Data class: Non-PII.'
    """)

    op.execute("""
        ALTER TABLE attribution_recompute_jobs
            ADD CONSTRAINT ck_attribution_recompute_jobs_run_count_positive
            CHECK (run_count >= 0)
    """)

    op.execute("""
        COMMENT ON CONSTRAINT ck_attribution_recompute_jobs_run_count_positive ON attribution_recompute_jobs IS
            'Validates run_count is non-negative. Purpose: Prevent invalid negative counts. Data class: Non-PII.'
    """)

    op.execute("""
        ALTER TABLE attribution_recompute_jobs
            ADD CONSTRAINT ck_attribution_recompute_jobs_window_bounds_valid
            CHECK (window_end > window_start)
    """)

    op.execute("""
        COMMENT ON CONSTRAINT ck_attribution_recompute_jobs_window_bounds_valid ON attribution_recompute_jobs IS
            'Validates window_end > window_start. Purpose: Prevent invalid zero or negative time windows. Data class: Non-PII.'
    """)

    # Create UNIQUE constraint for window-scoped idempotency
    # This is the critical constraint that prevents duplicate window executions
    op.execute("""
        CREATE UNIQUE INDEX idx_attribution_recompute_jobs_window_identity
            ON attribution_recompute_jobs (tenant_id, window_start, window_end, model_version)
    """)

    op.execute("""
        COMMENT ON INDEX idx_attribution_recompute_jobs_window_identity IS
            'CRITICAL IDEMPOTENCY CONSTRAINT: Enforces window-scoped uniqueness per (tenant_id, window_start, window_end, model_version). Purpose: Prevent duplicate job identity rows - rerunning the same window must not create a new job row, but instead reuse/update the existing one. This is the provable mechanism that prevents "Window Re-Run Produces Duplicates" failure mode. Any attempt to INSERT a duplicate window identity will raise a unique_violation error, which the task handler must catch and convert to an idempotent upsert.'
    """)

    # Create indexes for query performance
    op.execute("""
        CREATE INDEX idx_attribution_recompute_jobs_tenant_status
            ON attribution_recompute_jobs (tenant_id, status)
    """)

    op.execute("""
        COMMENT ON INDEX idx_attribution_recompute_jobs_tenant_status IS
            'Composite index on (tenant_id, status). Purpose: Enable fast queries for active jobs per tenant (e.g., find all running jobs, find all failed jobs). Supports operational dashboards.'
    """)

    op.execute("""
        CREATE INDEX idx_attribution_recompute_jobs_tenant_created_at
            ON attribution_recompute_jobs (tenant_id, created_at DESC)
    """)

    op.execute("""
        COMMENT ON INDEX idx_attribution_recompute_jobs_tenant_created_at IS
            'Composite index on (tenant_id, created_at). Purpose: Enable fast queries for recent jobs per tenant (e.g., job history, audit log). DESC order for time-series queries.'
    """)

    # Enable RLS
    op.execute("""
        ALTER TABLE attribution_recompute_jobs ENABLE ROW LEVEL SECURITY
    """)

    # Create RLS policy for tenant isolation
    op.execute("""
        CREATE POLICY attribution_recompute_jobs_tenant_isolation
            ON attribution_recompute_jobs
            FOR ALL
            USING (tenant_id::text = current_setting('app.current_tenant_id', TRUE))
            WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', TRUE))
    """)

    op.execute("""
        COMMENT ON POLICY attribution_recompute_jobs_tenant_isolation ON attribution_recompute_jobs IS
            'RLS policy for tenant isolation. Purpose: Ensure jobs are only visible/writable for the current tenant (app.current_tenant_id GUC). Prevents cross-tenant data leakage. Critical security control.'
    """)

    # Grant privileges to app_user
    op.execute("""
        GRANT SELECT, INSERT, UPDATE ON attribution_recompute_jobs TO app_user
    """)

    # Explicitly revoke DELETE (jobs are append-only for audit purposes)
    op.execute("""
        REVOKE DELETE ON attribution_recompute_jobs FROM app_user
    """)


def downgrade() -> None:
    """
    Rollback migration changes.

    Removes:
    1. RLS policy
    2. Indexes
    3. attribution_recompute_jobs table
    """

    # Drop RLS policy
    op.execute("DROP POLICY IF EXISTS attribution_recompute_jobs_tenant_isolation ON attribution_recompute_jobs")

    # Drop table (CASCADE will drop all constraints and indexes)
    op.execute("DROP TABLE IF EXISTS attribution_recompute_jobs CASCADE")
