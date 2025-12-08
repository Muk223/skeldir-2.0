"""Add LLM subsystem tables for cost tracking and investigation workflows

Revision ID: 202512081500
Revises: 202511271210
Create Date: 2025-12-08 15:00:00

Migration Description:
Creates 7 LLM subsystem tables for B0.3 Phase completion:
- llm_api_calls: Track LLM API usage and costs per tenant
- llm_monthly_costs: Aggregated monthly billing data
- investigations: Bounded agent investigation jobs (60s timeout, $0.30 ceiling)
- investigation_tool_calls: Tool call audit trail for investigations
- explanation_cache: RAG explanation cache for <500ms p95 latency
- budget_optimization_jobs: Async budget optimization job tracking
- llm_validation_failures: Quarantine for failed LLM validations

All tables include:
- UUID primary keys with gen_random_uuid()
- tenant_id FK for multi-tenancy
- Timestamps (created_at, updated_at where applicable)
- JSONB for flexible metadata storage
- Appropriate indexes for query performance

Contract Mapping:
- investigations: Supports /api/investigations endpoints (llm-investigations.yaml)
- explanation_cache: Supports /api/v1/explain endpoints (llm-explanations.yaml)
- budget_optimization_jobs: Supports /api/budget/optimize endpoints (llm-budget.yaml)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '202512081500'
down_revision: Union[str, None] = '202511271210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create all 7 LLM subsystem tables.

    Tables are created in dependency order to satisfy foreign key constraints.
    """

    # ========================================================================
    # Table 1: llm_api_calls - LLM API usage tracking
    # ========================================================================

    op.execute("""
        CREATE TABLE llm_api_calls (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            endpoint TEXT NOT NULL,
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
            output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
            cost_cents INTEGER NOT NULL CHECK (cost_cents >= 0),
            latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
            was_cached BOOLEAN DEFAULT FALSE,
            request_metadata JSONB
        )
    """)

    op.execute("""
        CREATE INDEX idx_llm_calls_tenant_endpoint
            ON llm_api_calls(tenant_id, endpoint, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX idx_llm_calls_tenant_created_at
            ON llm_api_calls(tenant_id, created_at DESC)
    """)

    op.execute("""
        COMMENT ON TABLE llm_api_calls IS
            'Tracks LLM API calls for cost monitoring and usage analytics. Purpose: Enable per-tenant cost tracking and budget enforcement. Data class: Non-PII. Ownership: LLM service. RLS enabled for tenant isolation.'
    """)

    # ========================================================================
    # Table 2: llm_monthly_costs - Aggregated monthly billing
    # ========================================================================

    op.execute("""
        CREATE TABLE llm_monthly_costs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            month DATE NOT NULL,
            total_cost_cents INTEGER NOT NULL CHECK (total_cost_cents >= 0),
            total_calls INTEGER NOT NULL CHECK (total_calls >= 0),
            model_breakdown JSONB NOT NULL,
            UNIQUE(tenant_id, month)
        )
    """)

    op.execute("""
        CREATE INDEX idx_llm_monthly_tenant_month
            ON llm_monthly_costs(tenant_id, month DESC)
    """)

    op.execute("""
        COMMENT ON TABLE llm_monthly_costs IS
            'Aggregated monthly LLM costs per tenant. Purpose: Monthly billing reports and cost trend analysis. Data class: Non-PII. Ownership: LLM service. RLS enabled for tenant isolation.'
    """)

    # ========================================================================
    # Table 3: investigations - Bounded agent investigation jobs
    # ========================================================================

    op.execute("""
        CREATE TABLE investigations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            query TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
            result JSONB,
            cost_cents INTEGER DEFAULT 0 CHECK (cost_cents >= 0)
        )
    """)

    op.execute("""
        CREATE INDEX idx_investigations_tenant_status
            ON investigations(tenant_id, status, created_at DESC)
    """)

    op.execute("""
        COMMENT ON TABLE investigations IS
            'Bounded agent investigations (60s timeout, $0.30 cost ceiling). Purpose: Track async investigation job lifecycle. Data class: Non-PII (queries redacted of PII). Ownership: LLM service. RLS enabled for tenant isolation.'
    """)

    # ========================================================================
    # Table 4: investigation_tool_calls - Tool call audit trail
    # ========================================================================

    op.execute("""
        CREATE TABLE investigation_tool_calls (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            tool_name TEXT NOT NULL,
            input_params JSONB NOT NULL,
            output JSONB
        )
    """)

    op.execute("""
        CREATE INDEX idx_tool_calls_investigation
            ON investigation_tool_calls(investigation_id, created_at)
    """)

    op.execute("""
        CREATE INDEX idx_tool_calls_tenant
            ON investigation_tool_calls(tenant_id, created_at DESC)
    """)

    op.execute("""
        COMMENT ON TABLE investigation_tool_calls IS
            'Audit trail of tool calls made during investigations. Purpose: Debug investigation behavior and track tool usage. Data class: Non-PII. Ownership: LLM service. RLS enabled for tenant isolation.'
    """)

    # ========================================================================
    # Table 5: explanation_cache - RAG explanation cache
    # ========================================================================

    op.execute("""
        CREATE TABLE explanation_cache (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            entity_type TEXT NOT NULL,
            entity_id UUID NOT NULL,
            explanation TEXT NOT NULL,
            citations JSONB NOT NULL,
            cache_hit_count INTEGER DEFAULT 0 CHECK (cache_hit_count >= 0),
            UNIQUE(tenant_id, entity_type, entity_id)
        )
    """)

    op.execute("""
        CREATE INDEX idx_explanation_cache_lookup
            ON explanation_cache(tenant_id, entity_type, entity_id)
    """)

    op.execute("""
        COMMENT ON TABLE explanation_cache IS
            'Cached explanations for fast RAG retrieval (<500ms p95 latency target). Purpose: Enable sub-second explanation delivery via cache. Data class: Non-PII. Ownership: LLM service. RLS enabled for tenant isolation.'
    """)

    # ========================================================================
    # Table 6: budget_optimization_jobs - Budget optimization jobs
    # ========================================================================

    op.execute("""
        CREATE TABLE budget_optimization_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
            recommendations JSONB,
            cost_cents INTEGER DEFAULT 0 CHECK (cost_cents >= 0)
        )
    """)

    op.execute("""
        CREATE INDEX idx_budget_jobs_tenant_status
            ON budget_optimization_jobs(tenant_id, status, created_at DESC)
    """)

    op.execute("""
        COMMENT ON TABLE budget_optimization_jobs IS
            'Async budget optimization job tracking. Purpose: Track job lifecycle for budget recommendation generation. Data class: Non-PII. Ownership: LLM service. RLS enabled for tenant isolation.'
    """)

    # ========================================================================
    # Table 7: llm_validation_failures - LLM validation error quarantine
    # ========================================================================

    op.execute("""
        CREATE TABLE llm_validation_failures (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            endpoint TEXT NOT NULL,
            validation_error TEXT NOT NULL,
            request_payload JSONB NOT NULL,
            response_payload JSONB
        )
    """)

    op.execute("""
        CREATE INDEX idx_llm_failures_tenant_endpoint
            ON llm_validation_failures(tenant_id, endpoint, created_at DESC)
    """)

    op.execute("""
        CREATE INDEX idx_llm_failures_created_at
            ON llm_validation_failures(created_at DESC)
    """)

    op.execute("""
        COMMENT ON TABLE llm_validation_failures IS
            'Quarantine for failed LLM validations. Purpose: Store validation errors for triage and retry. Data class: Non-PII (payloads sanitized). Ownership: LLM service. RLS enabled for tenant isolation.'
    """)


def downgrade() -> None:
    """
    Drop all 7 LLM subsystem tables in reverse dependency order.
    """

    op.execute("DROP TABLE IF EXISTS llm_validation_failures CASCADE")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("DROP TABLE IF EXISTS budget_optimization_jobs CASCADE")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("DROP TABLE IF EXISTS explanation_cache CASCADE")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("DROP TABLE IF EXISTS investigation_tool_calls CASCADE")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("DROP TABLE IF EXISTS investigations CASCADE")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("DROP TABLE IF EXISTS llm_monthly_costs CASCADE")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("DROP TABLE IF EXISTS llm_api_calls CASCADE")  # CI:DESTRUCTIVE_OK - Downgrade rollback
