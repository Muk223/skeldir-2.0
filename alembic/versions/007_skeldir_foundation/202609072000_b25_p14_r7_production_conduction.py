"""P14 VII: final issuance mapping, governed tenant policy and elapsed freshness.

Revision ID: 202609072000
Revises: 202609071200
"""

from alembic import op
import sqlalchemy as sa

revision = "202609072000"
down_revision = "202609071200"
branch_labels = None
depends_on = None


def _replace_function(name: str, old: str, new: str) -> None:
    connection = op.get_bind()
    definition = connection.execute(
        sa.text("SELECT pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='public'::regnamespace AND proname=:name"),
        {"name": name},
    ).scalar_one()
    if old not in definition:
        raise RuntimeError(f"P14 VII migration predecessor mismatch: {name}")
    op.execute(definition.replace(old, new))


def _grant_if_role_exists(role: str, statement: str) -> None:
    # Repository convention from 202609071200: migrations must run on a bare
    # database where app roles may not exist (B0/B1 lanes migrate as bare
    # postgres with no provisioned role graph). Unconditional GRANT/REVOKE
    # to a missing role aborts the whole migration with UndefinedObject.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{role}')
            THEN
                EXECUTE $stmt${statement}$stmt$;
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.execute("""
        CREATE VIEW public.trust_final_issuance_identity
        WITH (security_barrier=true) AS
        SELECT history.tenant_id, history.envelope_hash,
               history.semantic_truth_hash AS audit_stage_semantic_truth_hash,
               history.access_audit_ref, history.subject_type, history.subject_ref_hash,
               attempt.id AS attempt_id,
               attempt.signed_envelope_hash AS final_envelope_hash,
               attempt.signed_envelope->>'semantic_truth_hash' AS semantic_truth_hash,
               attempt.signed_envelope->>'envelope_id' AS source_envelope_id,
               attempt.signed_envelope->'policy_action_authority'->>'policy_state' AS policy_state,
               attempt.signed_envelope AS signed_envelope
        FROM public.trust_envelope_issuance_log history
        JOIN public.trust_access_log ledger
          ON ledger.tenant_id=history.tenant_id AND ledger.audit_ref=history.access_audit_ref
        JOIN public.trust_issuance_attempts attempt
          ON attempt.tenant_id=ledger.tenant_id AND attempt.audit_ref=ledger.audit_ref
         AND attempt.id=ledger.issued_attempt_id
        WHERE history.tenant_id=current_setting('app.current_tenant_id',true)::uuid
          AND history.status='success' AND ledger.issuance_state='issued'
          AND attempt.attempt_state='issued'
          AND attempt.signed_envelope IS NOT DISTINCT FROM ledger.issued_envelope
          AND attempt.signature IS NOT DISTINCT FROM ledger.issued_signature
          AND attempt.signature_hash IS NOT DISTINCT FROM ledger.issued_signature_hash
          AND attempt.signing_key_id IS NOT DISTINCT FROM ledger.issued_signing_key_id;
        REVOKE ALL ON public.trust_final_issuance_identity FROM PUBLIC;
        COMMENT ON VIEW public.trust_final_issuance_identity IS
          'Explicit audit-stage to final signer-confirmed artifact mapping. envelope_hash remains the immutable audit-stage foreign key; final_envelope_hash identifies the retained final artifact.';
    """)
    for _role in ("app_user", "app_worker", "app_b28_requester", "app_b28_solver", "app_trust_issuer"):
        _grant_if_role_exists(_role, f"GRANT SELECT ON public.trust_final_issuance_identity TO {_role}")
    for name in ("b27_enforce_explanation_consequence", "b28_enforce_request_consequence", "b28_enforce_result_consequence"):
        _replace_function(name, "FROM public.trust_envelope_issuance_log", "FROM public.trust_final_issuance_identity")

    op.execute("""
        CREATE TABLE public.trust_tenant_policy_events (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
          revision bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
          policy_state text NOT NULL CHECK (policy_state IN
            ('blocked','read_only','simulation_only','proposal_required','approval_required')),
          approval_reference text NOT NULL CHECK (length(approval_reference) BETWEEN 1 AND 200),
          published_by name NOT NULL DEFAULT session_user CHECK (published_by='app_trust_policy_admin'),
          created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        );
        CREATE INDEX ix_trust_tenant_policy_latest ON public.trust_tenant_policy_events(tenant_id,revision DESC);
        ALTER TABLE public.trust_tenant_policy_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.trust_tenant_policy_events FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation_policy_trust_tenant_policy_events ON public.trust_tenant_policy_events
          USING (tenant_id=current_setting('app.current_tenant_id',true)::uuid)
          WITH CHECK (tenant_id=current_setting('app.current_tenant_id',true)::uuid);
        REVOKE ALL ON public.trust_tenant_policy_events FROM PUBLIC;
        -- The publisher role is provisioned by
        -- scripts/database/prepare_migration_authority_boundary.py, never by
        -- migrations: CREATE ROLE here would fail for restricted migration
        -- users (only CREATEROLE roles may create roles) on lanes that
        -- migrate without the full role graph. Grants below are
        -- role-tolerant; the role itself arrives via provisioning.
        CREATE FUNCTION public.trust_tenant_policy_append_only() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
        BEGIN
          IF TG_OP='DELETE' AND NOT EXISTS (SELECT 1 FROM public.tenants WHERE id=OLD.tenant_id) THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION 'trust_policy_append_only' USING ERRCODE='42501';
        END $$;
        CREATE TRIGGER trg_trust_policy_append_only BEFORE UPDATE OR DELETE ON public.trust_tenant_policy_events
          FOR EACH ROW EXECUTE FUNCTION public.trust_tenant_policy_append_only();

        CREATE FUNCTION public.b28_enforce_final_source_identity() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
        DECLARE source_id text; source_policy text; current_policy text;
          states text[] := ARRAY['blocked','read_only','simulation_only','proposal_required','approval_required'];
        BEGIN
          SELECT source_envelope_id,policy_state INTO source_id,source_policy FROM public.trust_final_issuance_identity
            WHERE tenant_id=NEW.tenant_id AND envelope_hash=NEW.source_issuance_envelope_hash;
          IF source_id IS NOT NULL AND source_id IS DISTINCT FROM NEW.source_envelope_id THEN
            RAISE EXCEPTION 'b28_request_final_identity_mismatch' USING ERRCODE='42501';
          END IF;
          SELECT policy_state INTO current_policy FROM public.trust_tenant_policy_events
            WHERE tenant_id=NEW.tenant_id ORDER BY revision DESC LIMIT 1;
          IF COALESCE(current_policy,'read_only') NOT IN ('simulation_only','proposal_required','approval_required')
             OR array_position(states,source_policy)>array_position(states,current_policy) THEN
            RAISE EXCEPTION 'b28_request_current_policy_forbids' USING ERRCODE='42501';
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_b28_final_source_identity BEFORE INSERT ON public.b28_simulation_requests
          FOR EACH ROW EXECUTE FUNCTION public.b28_enforce_final_source_identity();
    """)
    for _role in ("app_user", "app_worker", "app_rw", "app_ro"):
        _grant_if_role_exists(_role, f"REVOKE ALL ON public.trust_tenant_policy_events FROM {_role}")
    for _role in ("app_user", "app_worker", "app_b28_requester", "app_b28_solver"):
        _grant_if_role_exists(_role, f"GRANT SELECT ON public.trust_tenant_policy_events TO {_role}")
    _grant_if_role_exists("app_trust_policy_admin", "GRANT USAGE ON SCHEMA public TO app_trust_policy_admin")
    _grant_if_role_exists("app_trust_policy_admin", "GRANT INSERT,SELECT ON public.trust_tenant_policy_events TO app_trust_policy_admin")
    _grant_if_role_exists("app_trust_policy_admin", "GRANT USAGE ON SEQUENCE public.trust_tenant_policy_events_revision_seq TO app_trust_policy_admin")
    for name in ("b28_authenticate_request_possession", "b28_enforce_request_possession"):
        _replace_function(name, "now()", "clock_timestamp()")
    for table, column in (("b28_request_authentications", "authenticated_at"), ("b28_simulation_requests", "requested_at"), ("b28_simulation_results", "created_at"), ("b28_proposals", "created_at")):
        op.execute(f"ALTER TABLE public.{table} ALTER COLUMN {column} SET DEFAULT clock_timestamp()")
        op.execute(f"COMMENT ON COLUMN public.{table}.{column} IS 'OBSERVED EVENT. Database wall-clock row construction time; not transaction start or commit time.'")


def downgrade() -> None:
    """Restore the ``202609071200`` contract exactly (C16/C17 reversibility).

    VII-3 requires the chain to remain round-trippable as the non-superuser
    owner: ``downgrade 202608291200`` traverses this revision, so a
    forward-only stub strands every reversibility lane. Each step below
    reverses the corresponding upgrade step; destructive drops carry the
    CI:DESTRUCTIVE_OK marker per repository convention.
    """
    # CI:DESTRUCTIVE_OK - downgrade rollback; this revision created the trigger.
    op.execute("DROP TRIGGER IF EXISTS trg_b28_final_source_identity ON public.b28_simulation_requests")
    # CI:DESTRUCTIVE_OK - downgrade rollback; this revision created the function.
    op.execute("DROP FUNCTION IF EXISTS public.b28_enforce_final_source_identity()")
    # CI:DESTRUCTIVE_OK - downgrade rollback; this revision created the trigger.
    op.execute("DROP TRIGGER IF EXISTS trg_trust_policy_append_only ON public.trust_tenant_policy_events")
    # CI:DESTRUCTIVE_OK - downgrade rollback; this revision created the function.
    op.execute("DROP FUNCTION IF EXISTS public.trust_tenant_policy_append_only()")
    # CI:DESTRUCTIVE_OK - downgrade rollback; this revision created the table.
    op.execute("DROP TABLE IF EXISTS public.trust_tenant_policy_events")  # CI:DESTRUCTIVE_OK - downgrade rollback of VII policy table
    # CI:DESTRUCTIVE_OK - downgrade rollback; this revision created the view.
    op.execute("DROP VIEW IF EXISTS public.trust_final_issuance_identity")
    for name in ("b27_enforce_explanation_consequence", "b28_enforce_request_consequence", "b28_enforce_result_consequence"):
        _replace_function(name, "FROM public.trust_final_issuance_identity", "FROM public.trust_envelope_issuance_log")
    for name in ("b28_authenticate_request_possession", "b28_enforce_request_possession"):
        _replace_function(name, "clock_timestamp()", "now()")
    for table, column in (("b28_request_authentications", "authenticated_at"), ("b28_simulation_requests", "requested_at"), ("b28_simulation_results", "created_at"), ("b28_proposals", "created_at")):
        op.execute(f"ALTER TABLE public.{table} ALTER COLUMN {column} SET DEFAULT now()")
