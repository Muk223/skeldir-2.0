"""Add audit triggers for channel state transitions and assignment corrections

Revision ID: 202511171530
Revises: 202511171520
Create Date: 2025-11-17 15:30:00.000000

Phase 3 of Channel Governance Auditability Implementation

This migration creates database triggers to automatically log:
1. Channel taxonomy state transitions to channel_state_transitions
2. Channel assignment corrections to channel_assignment_corrections

Trigger Functions:
- fn_log_channel_state_change(): Logs taxonomy state transitions
- fn_log_channel_assignment_correction(): Logs assignment corrections

Triggers:
- trg_channel_taxonomy_state_audit: Fires on channel_taxonomy.state changes
- trg_allocations_channel_correction_audit: Fires on attribution_allocations.channel_code changes

This migration is BLOCKING for:
- Channel auditability system (triggers are the enforcement mechanism)
- Compliance and PE-readiness requirements

Exit Gates:
- Migration applies cleanly
- Trigger functions exist and are SECURITY DEFINER
- Triggers fire on state/assignment changes
- Audit rows are created atomically
"""

from alembic import op
import sqlalchemy as sa
from typing import Union


# revision identifiers, used by Alembic.
revision: str = '202511171530'
down_revision: Union[str, None] = '202511171520'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """
    Create trigger functions and attach triggers.
    
    Implementation:
    1. Create fn_log_channel_state_change() function
    2. Create trg_channel_taxonomy_state_audit trigger
    3. Create fn_log_channel_assignment_correction() function
    4. Create trg_allocations_channel_correction_audit trigger
    """
    
    # ========================================================================
    # Step 1: Create trigger function for channel state transitions
    # ========================================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_log_channel_state_change()
        RETURNS TRIGGER AS $$
        DECLARE
            change_by_val VARCHAR(255);
            change_reason_val TEXT;
        BEGIN
            -- Only log if the 'state' column actually changed
            IF (NEW.state IS DISTINCT FROM OLD.state) THEN
                -- Read session variables set by application layer
                -- Fall back to 'system' if unset (indicates bypass attempt)
                change_by_val := COALESCE(
                    current_setting('app.channel_state_change_by', true),
                    'system'
                );
                change_reason_val := NULLIF(
                    current_setting('app.channel_state_change_reason', true),
                    ''
                );
                
                -- Insert audit record
                INSERT INTO channel_state_transitions (
                    channel_code,
                    from_state,
                    to_state,
                    changed_by,
                    changed_at,
                    reason
                )
                VALUES (
                    NEW.code,
                    OLD.state,
                    NEW.state,
                    change_by_val,
                    NOW(),
                    change_reason_val
                );
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    op.execute("""
        COMMENT ON FUNCTION fn_log_channel_state_change() IS 
            'Trigger function to log channel_taxonomy state transitions to channel_state_transitions table. 
            Purpose: Ensure every state change produces a corresponding audit row. 
            Invariant: No taxonomy state change without matching transition row. 
            Security: SECURITY DEFINER to ensure trigger can insert audit records.'
    """)
    
    # ========================================================================
    # Step 2: Create trigger on channel_taxonomy
    # ========================================================================
    
    op.execute("""
        CREATE TRIGGER trg_channel_taxonomy_state_audit
        AFTER UPDATE OF state ON channel_taxonomy
        FOR EACH ROW
        WHEN (OLD.state IS DISTINCT FROM NEW.state)
        EXECUTE FUNCTION fn_log_channel_state_change();
    """)
    
    op.execute("""
        COMMENT ON TRIGGER trg_channel_taxonomy_state_audit ON channel_taxonomy IS 
            'Automatically logs all state transitions to channel_state_transitions table. 
            Purpose: Provide atomic audit trail for channel lifecycle changes. 
            Fires: Only when state column changes (not on other column updates).'
    """)
    
    # ========================================================================
    # Step 3: Create trigger function for assignment corrections
    # ========================================================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_log_channel_assignment_correction()
        RETURNS TRIGGER AS $$
        DECLARE
            correction_by_val VARCHAR(255);
            correction_reason_val TEXT;
        BEGIN
            -- Only log if the 'channel_code' column actually changed
            IF (NEW.channel_code IS DISTINCT FROM OLD.channel_code) THEN
                -- Read session variables set by application layer
                -- Fall back to 'system' if unset (indicates bypass attempt)
                correction_by_val := COALESCE(
                    current_setting('app.correction_by', true),
                    'system'
                );
                correction_reason_val := COALESCE(
                    NULLIF(current_setting('app.correction_reason', true), ''),
                    'No reason provided'
                );
                
                -- Insert audit record
                INSERT INTO channel_assignment_corrections (
                    tenant_id,
                    entity_type,
                    entity_id,
                    from_channel,
                    to_channel,
                    corrected_by,
                    corrected_at,
                    reason
                )
                VALUES (
                    NEW.tenant_id,
                    'allocation',
                    NEW.id,
                    OLD.channel_code,
                    NEW.channel_code,
                    correction_by_val,
                    NOW(),
                    correction_reason_val
                );
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    op.execute("""
        COMMENT ON FUNCTION fn_log_channel_assignment_correction() IS 
            'Trigger function to log attribution_allocations channel_code corrections to channel_assignment_corrections table. 
            Purpose: Ensure every post-ingestion assignment correction produces a corresponding audit row. 
            Invariant: No assignment correction without matching correction row. 
            Security: SECURITY DEFINER to bypass RLS during trigger execution (reads tenant_id from allocation, already RLS-protected).'
    """)
    
    # ========================================================================
    # Step 4: Create trigger on attribution_allocations
    # ========================================================================
    
    op.execute("""
        CREATE TRIGGER trg_allocations_channel_correction_audit
        AFTER UPDATE OF channel_code ON attribution_allocations
        FOR EACH ROW
        WHEN (OLD.channel_code IS DISTINCT FROM NEW.channel_code)
        EXECUTE FUNCTION fn_log_channel_assignment_correction();
    """)
    
    op.execute("""
        COMMENT ON TRIGGER trg_allocations_channel_correction_audit ON attribution_allocations IS 
            'Automatically logs all channel_code corrections to channel_assignment_corrections table. 
            Purpose: Provide atomic audit trail for revenue reclassifications. 
            Fires: Only when channel_code column changes (not on other column updates). 
            Note: Does NOT fire on INSERT (corrections are post-ingestion only).'
    """)
    
    # ========================================================================
    # Step 5: Log completion
    # ========================================================================
    
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE 'Channel audit triggers created';
            RAISE NOTICE 'trg_channel_taxonomy_state_audit: Logs state transitions';
            RAISE NOTICE 'trg_allocations_channel_correction_audit: Logs assignment corrections';
            RAISE NOTICE 'All triggers use SECURITY DEFINER for audit record insertion';
        END $$;
    """)


def downgrade() -> None:
    """
    Drop audit triggers and trigger functions.
    
    WARNING: This rollback removes automatic audit logging.
    After this migration is rolled back, state changes and corrections must be logged manually.
    """
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_allocations_channel_correction_audit ON attribution_allocations")
    op.execute("DROP TRIGGER IF EXISTS trg_channel_taxonomy_state_audit ON channel_taxonomy")
    
    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS fn_log_channel_assignment_correction()")
    op.execute("DROP FUNCTION IF EXISTS fn_log_channel_state_change()")
    
    # Log rollback
    op.execute("""
        DO $$
        BEGIN
            RAISE WARNING 'Channel audit triggers dropped';
            RAISE WARNING 'Automatic audit logging disabled';
            RAISE WARNING 'State changes and corrections must be logged manually';
        END $$;
    """)

