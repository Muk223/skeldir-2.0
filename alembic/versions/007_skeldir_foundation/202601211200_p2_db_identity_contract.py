"""B0.5.7-P2: Production-truth DB identity contract (least privilege is testable).

Establishes a deterministic privilege boundary:
- Runtime role(s) cannot SELECT from public.tenants directly.
- Narrow SECURITY DEFINER interfaces mediate required access.
- Runtime role(s) can perform required LLM audit writes under RLS.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "202601211200"
down_revision: Union[str, None] = "202601131610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dedicated definer role for privileged routines (no login; no membership grants).
    # NOTE: BYPASSRLS is required for deterministic tenant resolution even if tenants
    # becomes FORCE RLS in production snapshots.
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_security') THEN
            CREATE ROLE app_security NOLOGIN INHERIT BYPASSRLS;
          END IF;
        END
        $$;
        """
    )

    # Ensure definer role can read tenants (still inaccessible to runtime roles).
    op.execute("GRANT USAGE ON SCHEMA public TO app_security;")
    op.execute("GRANT SELECT ON TABLE public.tenants TO app_security;")

    # Enforce tenant table deny-by-default at the table privilege layer.
    op.execute("REVOKE ALL ON TABLE public.tenants FROM PUBLIC;")
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
            REVOKE ALL ON TABLE public.tenants FROM app_rw;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
            REVOKE ALL ON TABLE public.tenants FROM app_user;
          END IF;
        END
        $$;
        """
    )

    # SECURITY DEFINER routines live in a dedicated schema.
    op.execute("CREATE SCHEMA IF NOT EXISTS security AUTHORIZATION app_security;")
    op.execute("REVOKE ALL ON SCHEMA security FROM PUBLIC;")
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
            GRANT USAGE ON SCHEMA security TO app_rw;
          END IF;
        END
        $$;
        """
    )

    # List tenant IDs for internal maintenance tasks (no secrets).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION security.list_tenant_ids()
        RETURNS TABLE(tenant_id uuid)
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
          SELECT id AS tenant_id
          FROM public.tenants
          ORDER BY id
        $$;
        """
    )
    op.execute("ALTER FUNCTION security.list_tenant_ids() OWNER TO app_security;")

    # Resolve tenant identity + webhook secrets by api_key_hash (no direct tenants grants).
    op.execute(
        """
        CREATE OR REPLACE FUNCTION security.resolve_tenant_webhook_secrets(api_key_hash text)
        RETURNS TABLE(
          tenant_id uuid,
          shopify_webhook_secret text,
          stripe_webhook_secret text,
          paypal_webhook_secret text,
          woocommerce_webhook_secret text
        )
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
          SELECT
            t.id AS tenant_id,
            t.shopify_webhook_secret,
            t.stripe_webhook_secret,
            t.paypal_webhook_secret,
            t.woocommerce_webhook_secret
          FROM public.tenants AS t
          WHERE t.api_key_hash = resolve_tenant_webhook_secrets.api_key_hash
          LIMIT 1
        $$;
        """
    )
    op.execute("ALTER FUNCTION security.resolve_tenant_webhook_secrets(text) OWNER TO app_security;")

    # Lock down function EXECUTE privileges (functions default to PUBLIC).
    op.execute("REVOKE ALL ON FUNCTION security.list_tenant_ids() FROM PUBLIC;")
    op.execute("REVOKE ALL ON FUNCTION security.resolve_tenant_webhook_secrets(text) FROM PUBLIC;")
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
            GRANT EXECUTE ON FUNCTION security.list_tenant_ids() TO app_rw;
            GRANT EXECUTE ON FUNCTION security.resolve_tenant_webhook_secrets(text) TO app_rw;
          END IF;
        END
        $$;
        """
    )

    # LLM subsystem: grant only what runtime code needs (RLS already enforced).
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
            RETURN;
          END IF;

          IF to_regclass('public.llm_api_calls') IS NOT NULL THEN
            GRANT SELECT, INSERT ON TABLE public.llm_api_calls TO app_rw;
            REVOKE ALL ON TABLE public.llm_api_calls FROM PUBLIC;
          END IF;

          IF to_regclass('public.llm_monthly_costs') IS NOT NULL THEN
            GRANT SELECT, INSERT, UPDATE ON TABLE public.llm_monthly_costs TO app_rw;
            REVOKE ALL ON TABLE public.llm_monthly_costs FROM PUBLIC;
          END IF;

          IF to_regclass('public.investigations') IS NOT NULL THEN
            GRANT SELECT, INSERT ON TABLE public.investigations TO app_rw;
            REVOKE ALL ON TABLE public.investigations FROM PUBLIC;
          END IF;

          IF to_regclass('public.budget_optimization_jobs') IS NOT NULL THEN
            GRANT SELECT, INSERT ON TABLE public.budget_optimization_jobs TO app_rw;
            REVOKE ALL ON TABLE public.budget_optimization_jobs FROM PUBLIC;
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
            IF to_regclass('public.llm_api_calls') IS NOT NULL THEN
              REVOKE ALL ON TABLE public.llm_api_calls FROM app_rw;
            END IF;
            IF to_regclass('public.llm_monthly_costs') IS NOT NULL THEN
              REVOKE ALL ON TABLE public.llm_monthly_costs FROM app_rw;
            END IF;
            IF to_regclass('public.investigations') IS NOT NULL THEN
              REVOKE ALL ON TABLE public.investigations FROM app_rw;
            END IF;
            IF to_regclass('public.budget_optimization_jobs') IS NOT NULL THEN
              REVOKE ALL ON TABLE public.budget_optimization_jobs FROM app_rw;
            END IF;
          END IF;
        END
        $$;
        """
    )

    op.execute("DROP FUNCTION IF EXISTS security.resolve_tenant_webhook_secrets(text);")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("DROP FUNCTION IF EXISTS security.list_tenant_ids();")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("DROP SCHEMA IF EXISTS security;")  # CI:DESTRUCTIVE_OK - Downgrade rollback
    op.execute("REVOKE SELECT ON TABLE public.tenants FROM app_security;")
    op.execute("DROP ROLE IF EXISTS app_security;")  # CI:DESTRUCTIVE_OK - Downgrade rollback

