"""B0.7-P3 LLM provider controls: reservation, shutoff metadata, cache, and audit columns.

Revision ID: 202602071100
Revises: 202602051220
Create Date: 2026-02-07 11:00:00
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "202602071100"
down_revision: Union[str, None] = "202602051220"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # llm_api_calls governance columns (single-path write semantics)
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE llm_api_calls ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
    op.execute("ALTER TABLE llm_api_calls ADD COLUMN block_reason TEXT")
    op.execute("ALTER TABLE llm_api_calls ADD COLUMN failure_reason TEXT")
    op.execute("ALTER TABLE llm_api_calls ADD COLUMN breaker_state TEXT NOT NULL DEFAULT 'closed'")
    op.execute(
        "ALTER TABLE llm_api_calls ADD COLUMN provider_attempted BOOLEAN NOT NULL DEFAULT false"
    )
    op.execute(
        "ALTER TABLE llm_api_calls ADD COLUMN budget_reservation_cents INTEGER NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE llm_api_calls ADD COLUMN budget_settled_cents INTEGER NOT NULL DEFAULT 0"
    )
    op.execute("ALTER TABLE llm_api_calls ADD COLUMN cache_key TEXT")
    op.execute("ALTER TABLE llm_api_calls ADD COLUMN cache_watermark BIGINT")
    op.execute(
        """
        ALTER TABLE llm_api_calls
        ADD CONSTRAINT ck_llm_api_calls_status_valid
        CHECK (status IN ('pending', 'success', 'blocked', 'failed', 'idempotent_replay'))
        """
    )
    op.execute(
        """
        ALTER TABLE llm_api_calls
        ADD CONSTRAINT ck_llm_api_calls_breaker_state_valid
        CHECK (breaker_state IN ('closed', 'open', 'half_open'))
        """
    )
    op.execute(
        """
        ALTER TABLE llm_api_calls
        ADD CONSTRAINT ck_llm_api_calls_budget_reservation_nonnegative
        CHECK (budget_reservation_cents >= 0)
        """
    )
    op.execute(
        """
        ALTER TABLE llm_api_calls
        ADD CONSTRAINT ck_llm_api_calls_budget_settled_nonnegative
        CHECK (budget_settled_cents >= 0)
        """
    )

    # ------------------------------------------------------------------
    # Monthly budget state + reservation ledger
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE llm_monthly_budget_state (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            month DATE NOT NULL,
            cap_cents INTEGER NOT NULL CHECK (cap_cents >= 0),
            spent_cents INTEGER NOT NULL DEFAULT 0 CHECK (spent_cents >= 0),
            reserved_cents INTEGER NOT NULL DEFAULT 0 CHECK (reserved_cents >= 0),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, user_id, month)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_llm_monthly_budget_state_tenant_user_month "
        "ON llm_monthly_budget_state(tenant_id, user_id, month DESC)"
    )

    op.execute(
        """
        CREATE TABLE llm_budget_reservations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            endpoint TEXT NOT NULL,
            request_id TEXT NOT NULL,
            month DATE NOT NULL,
            reserved_cents INTEGER NOT NULL CHECK (reserved_cents >= 0),
            settled_cents INTEGER NOT NULL DEFAULT 0 CHECK (settled_cents >= 0),
            state TEXT NOT NULL CHECK (state IN ('reserved', 'settled', 'released', 'blocked')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, user_id, endpoint, request_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_llm_budget_reservations_tenant_user_month "
        "ON llm_budget_reservations(tenant_id, user_id, month DESC)"
    )

    # ------------------------------------------------------------------
    # Semantic cache (Postgres-only)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE llm_semantic_cache (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            endpoint TEXT NOT NULL,
            cache_key TEXT NOT NULL,
            watermark BIGINT NOT NULL DEFAULT 0,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            response_text TEXT NOT NULL,
            response_metadata_ref JSONB,
            reasoning_trace_ref JSONB,
            input_tokens INTEGER NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
            output_tokens INTEGER NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
            cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (cost_cents >= 0),
            hit_count INTEGER NOT NULL DEFAULT 0 CHECK (hit_count >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (tenant_id, user_id, endpoint, cache_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_llm_semantic_cache_tenant_user_endpoint "
        "ON llm_semantic_cache(tenant_id, user_id, endpoint, updated_at DESC)"
    )

    # ------------------------------------------------------------------
    # Extend hourly shutoff state with explicit threshold/window metadata
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE llm_hourly_shutoff_state "
        "ADD COLUMN threshold_cents INTEGER NOT NULL DEFAULT 0 CHECK (threshold_cents >= 0)"
    )
    op.execute(
        "ALTER TABLE llm_hourly_shutoff_state "
        "ADD COLUMN total_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (total_cost_cents >= 0)"
    )
    op.execute(
        "ALTER TABLE llm_hourly_shutoff_state "
        "ADD COLUMN total_calls INTEGER NOT NULL DEFAULT 0 CHECK (total_calls >= 0)"
    )
    op.execute("ALTER TABLE llm_hourly_shutoff_state ADD COLUMN disabled_until TIMESTAMPTZ")
    op.execute(
        "CREATE INDEX idx_llm_hourly_shutoff_disabled_until "
        "ON llm_hourly_shutoff_state(tenant_id, user_id, disabled_until DESC)"
    )

    # ------------------------------------------------------------------
    # RLS and grants
    # ------------------------------------------------------------------
    for table_name in ("llm_monthly_budget_state", "llm_budget_reservations", "llm_semantic_cache"):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_policy ON {table_name}
                USING (
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                    AND user_id = current_setting('app.current_user_id', true)::uuid
                )
                WITH CHECK (
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                    AND user_id = current_setting('app.current_user_id', true)::uuid
                )
            """
        )

    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE llm_api_calls TO app_rw")
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE llm_breaker_state TO app_rw")
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE llm_hourly_shutoff_state TO app_rw")
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE llm_monthly_budget_state TO app_rw")
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE llm_budget_reservations TO app_rw")
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE llm_semantic_cache TO app_rw")


def downgrade() -> None:
    op.execute("REVOKE ALL ON TABLE llm_semantic_cache FROM app_rw")
    op.execute("REVOKE ALL ON TABLE llm_budget_reservations FROM app_rw")
    op.execute("REVOKE ALL ON TABLE llm_monthly_budget_state FROM app_rw")
    op.execute("REVOKE ALL ON TABLE llm_hourly_shutoff_state FROM app_rw")
    op.execute("REVOKE ALL ON TABLE llm_breaker_state FROM app_rw")
    op.execute("REVOKE ALL ON TABLE llm_api_calls FROM app_rw")

    op.execute("DROP INDEX IF EXISTS idx_llm_hourly_shutoff_disabled_until")
    op.execute("ALTER TABLE llm_hourly_shutoff_state DROP COLUMN IF EXISTS disabled_until")
    op.execute("ALTER TABLE llm_hourly_shutoff_state DROP COLUMN IF EXISTS total_calls")
    op.execute("ALTER TABLE llm_hourly_shutoff_state DROP COLUMN IF EXISTS total_cost_cents")
    op.execute("ALTER TABLE llm_hourly_shutoff_state DROP COLUMN IF EXISTS threshold_cents")

    op.execute("DROP TABLE IF EXISTS llm_semantic_cache CASCADE")  # CI:DESTRUCTIVE_OK
    op.execute("DROP TABLE IF EXISTS llm_budget_reservations CASCADE")  # CI:DESTRUCTIVE_OK
    op.execute("DROP TABLE IF EXISTS llm_monthly_budget_state CASCADE")  # CI:DESTRUCTIVE_OK

    op.execute("ALTER TABLE llm_api_calls DROP CONSTRAINT IF EXISTS ck_llm_api_calls_budget_settled_nonnegative")
    op.execute("ALTER TABLE llm_api_calls DROP CONSTRAINT IF EXISTS ck_llm_api_calls_budget_reservation_nonnegative")
    op.execute("ALTER TABLE llm_api_calls DROP CONSTRAINT IF EXISTS ck_llm_api_calls_breaker_state_valid")
    op.execute("ALTER TABLE llm_api_calls DROP CONSTRAINT IF EXISTS ck_llm_api_calls_status_valid")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS cache_watermark")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS cache_key")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS budget_settled_cents")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS budget_reservation_cents")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS provider_attempted")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS breaker_state")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS failure_reason")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS block_reason")
    op.execute("ALTER TABLE llm_api_calls DROP COLUMN IF EXISTS status")
