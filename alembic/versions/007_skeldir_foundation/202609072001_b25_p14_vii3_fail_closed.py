"""P14 VII-3: fail-closed final-source identity.

Revision ID: 202609072001
Revises: 202609072000

Agent-3 continuation (VII-3 H-VII3-04). The VII final-source trigger must
refuse when no final identity row matches, not silently continue to the
policy check where a permissive current policy would admit an unknown
source. The refusal reuses the durable-issuance error the downstream
request consequence guard raises, so the VII-2 selector proofs keep
adjudicating the same law at either layer.
"""

from alembic import op

revision = "202609072001"
down_revision = "202609072000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.b28_enforce_final_source_identity()
        RETURNS trigger
        LANGUAGE plpgsql SET search_path TO 'pg_catalog', 'public' AS $$
        DECLARE source_id text; source_policy text; current_policy text;
          states text[] := ARRAY['blocked','read_only','simulation_only','proposal_required','approval_required'];
        BEGIN
          SELECT source_envelope_id,policy_state INTO source_id,source_policy
            FROM public.trust_final_issuance_identity
            WHERE tenant_id=NEW.tenant_id
              AND envelope_hash=NEW.source_issuance_envelope_hash;
          IF source_id IS NULL THEN
            RAISE EXCEPTION 'b28_request_requires_durable_issuance:%',
              NEW.source_issuance_envelope_hash USING ERRCODE='42501';
          END IF;
          IF source_id IS DISTINCT FROM NEW.source_envelope_id THEN
            RAISE EXCEPTION 'b28_request_final_identity_mismatch'
              USING ERRCODE='42501';
          END IF;
          SELECT policy_state INTO current_policy
            FROM public.trust_tenant_policy_events
            WHERE tenant_id=NEW.tenant_id ORDER BY revision DESC LIMIT 1;
          IF COALESCE(current_policy,'read_only')
               NOT IN ('simulation_only','proposal_required','approval_required')
             OR array_position(states,source_policy)
                > array_position(states,current_policy) THEN
            RAISE EXCEPTION 'b28_request_current_policy_forbids'
              USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$;
    """)
    # Converge timestamp semantics comments: databases migrated before the
    # VII comment text was finalized retain the older physically_observed
    # phrasing, which the field-semantics taxonomy does not classify.
    # Re-assert the canonical OBSERVED EVENT text so empty->head and
    # predecessor->head construct identical catalogs.
    for table, column in (("b28_request_authentications", "authenticated_at"), ("b28_simulation_requests", "requested_at"), ("b28_simulation_results", "created_at"), ("b28_proposals", "created_at")):
        op.execute(f"ALTER TABLE public.{table} ALTER COLUMN {column} SET DEFAULT clock_timestamp()")
        op.execute(f"COMMENT ON COLUMN public.{table}.{column} IS 'OBSERVED EVENT. Database wall-clock row construction time; not transaction start or commit time.'")


def downgrade() -> None:
    raise RuntimeError("P14 VII-3 fail-closed mapping is forward-only")
