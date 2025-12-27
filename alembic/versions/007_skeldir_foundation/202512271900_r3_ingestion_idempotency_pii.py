"""R3 ingestion hardening: tenant-correct idempotency + deep PII guardrail.

R3 mandates:
- Idempotency must be tenant-scoped (no cross-tenant collisions)
- PII defense must be robust against nested JSON objects (not top-level only)
"""

from alembic import op
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "202512271900"
down_revision: Union[str, None] = "202512201000"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


PII_KEYS = [
    "email",
    "email_address",
    "phone",
    "phone_number",
    "ssn",
    "social_security_number",
    "ip_address",
    "ip",
    "first_name",
    "last_name",
    "full_name",
    "address",
    "street_address",
]


def upgrade() -> None:
    # ---------------------------------------------------------------------
    # Tenant-correct idempotency: (tenant_id, idempotency_key)
    # ---------------------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS idx_events_idempotency")

    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_attribution_events_tenant_idempotency_key'
          ) THEN
            ALTER TABLE public.attribution_events
              ADD CONSTRAINT uq_attribution_events_tenant_idempotency_key
              UNIQUE (tenant_id, idempotency_key);
          END IF;
        END
        $$;
        """
    )

    # ---------------------------------------------------------------------
    # Deep PII guardrail (jsonpath, any depth)
    # ---------------------------------------------------------------------
    pii_or_clauses = " OR ".join([f"jsonb_path_exists(payload, '$.**.{k}')" for k in PII_KEYS])
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION fn_detect_pii_keys(payload JSONB)
        RETURNS BOOLEAN AS $$
        BEGIN
            IF payload IS NULL THEN
                RETURN FALSE;
            END IF;
            RETURN ({pii_or_clauses});
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
        """
    )

    # Keep error messages stable with "Key found: <key>" (first match wins)
    detection_cases = "\n".join(
        [f"            IF jsonb_path_exists(NEW.raw_payload, '$.**.{k}') THEN detected_key := '{k}'; END IF;" for k in PII_KEYS]
    )
    detection_cases_metadata = "\n".join(
        [f"            IF jsonb_path_exists(NEW.metadata, '$.**.{k}') THEN detected_key := '{k}'; END IF;" for k in PII_KEYS]
    )

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION fn_enforce_pii_guardrail()
        RETURNS TRIGGER AS $$
        DECLARE
            detected_key TEXT;
        BEGIN
            IF TG_TABLE_NAME IN ('attribution_events', 'dead_events') THEN
                IF fn_detect_pii_keys(NEW.raw_payload) THEN
                    detected_key := NULL;
{detection_cases}
                    RAISE EXCEPTION
                      'PII key detected in %.raw_payload. Ingestion blocked by database policy (Layer 2 guardrail). Key found: %. Reference: ADR-003-PII-Defense-Strategy.md. Action: Remove PII key from payload before retry.',
                      TG_TABLE_NAME,
                      COALESCE(detected_key, 'unknown')
                    USING ERRCODE = '23514';
                END IF;
            END IF;

            IF TG_TABLE_NAME = 'revenue_ledger' THEN
                IF NEW.metadata IS NOT NULL THEN
                    IF fn_detect_pii_keys(NEW.metadata) THEN
                        detected_key := NULL;
{detection_cases_metadata}
                        RAISE EXCEPTION
                          'PII key detected in revenue_ledger.metadata. Write blocked by database policy (Layer 2 guardrail). Key found: %. Reference: ADR-003-PII-Defense-Strategy.md. Action: Remove PII key from metadata before retry.',
                          COALESCE(detected_key, 'unknown')
                        USING ERRCODE = '23514';
                    END IF;
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.attribution_events
          DROP CONSTRAINT IF EXISTS uq_attribution_events_tenant_idempotency_key;
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_events_idempotency
          ON public.attribution_events USING btree (idempotency_key);
        """
    )

