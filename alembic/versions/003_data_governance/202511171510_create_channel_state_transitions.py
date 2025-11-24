"""Create channel_state_transitions audit table

Revision ID: 202511171510
Revises: 202511171500
Create Date: 2025-11-17 15:10:00.000000

Phase 4 of Channel Governance Auditability Implementation

This migration creates the channel_state_transitions audit table to log
all state changes on channel_taxonomy:
1. Creates channel_state_transitions table
2. Adds indexes for chronological and state queries
3. Sets up FK relationship to channel_taxonomy

This migration is BLOCKING for:
- Channel auditability system
- Compliance and PE-readiness requirements

Exit Gates:
- Migration applies cleanly
- Table exists with correct schema
- Indexes support query patterns
"""

from alembic import op
import sqlalchemy as sa
from typing import Union


# revision identifiers, used by Alembic.
revision: str = '202511171510'
down_revision: Union[str, None] = '202511171500'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """
    Create channel_state_transitions audit table.
    
    Implementation:
    1. Create table with all required columns
    2. Add primary key and indexes
    3. Add FK constraint to channel_taxonomy
    4. Add table and column comments
    """
    
    # Step 1: Create channel_state_transitions table
    op.execute("""
        CREATE TABLE channel_state_transitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            channel_code VARCHAR(50) NOT NULL REFERENCES channel_taxonomy(code) ON DELETE CASCADE,
            from_state VARCHAR(50),
            to_state VARCHAR(50) NOT NULL,
            changed_by VARCHAR(255) NOT NULL,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            reason TEXT,
            metadata JSONB
        )
    """)
    
    # Step 2: Add indexes for query patterns
    # Index for chronological queries per channel
    op.execute("""
        CREATE INDEX idx_channel_state_transitions_channel_changed_at 
        ON channel_state_transitions (channel_code, changed_at DESC)
    """)
    
    # Index for state queries (recently deprecated channels)
    op.execute("""
        CREATE INDEX idx_channel_state_transitions_to_state_changed_at 
        ON channel_state_transitions (to_state, changed_at DESC)
    """)
    
    # Step 3: Add table comment
    op.execute("""
        COMMENT ON TABLE channel_state_transitions IS 
            'Audit log of all channel_taxonomy state transitions. Purpose: Provide immutable audit trail for channel lifecycle changes, enabling compliance and PE-readiness. Data class: Non-PII. Ownership: Data Governance.'
    """)
    
    # Step 4: Add column comments
    op.execute("""
        COMMENT ON COLUMN channel_state_transitions.id IS 
            'Primary key for transition record. Data class: Non-PII.'
    """)
    
    op.execute("""
        COMMENT ON COLUMN channel_state_transitions.channel_code IS 
            'Channel that transitioned (FK to channel_taxonomy.code). Data class: Non-PII.'
    """)
    
    op.execute("""
        COMMENT ON COLUMN channel_state_transitions.from_state IS 
            'Previous state (NULL for first assignment). Data class: Non-PII.'
    """)
    
    op.execute("""
        COMMENT ON COLUMN channel_state_transitions.to_state IS 
            'New state after transition. Data class: Non-PII.'
    """)
    
    op.execute("""
        COMMENT ON COLUMN channel_state_transitions.changed_by IS 
            'User/service that triggered transition (e.g., admin@skeldir.com, migration:20251117). Data class: Non-PII.'
    """)
    
    op.execute("""
        COMMENT ON COLUMN channel_state_transitions.changed_at IS 
            'Timestamp when transition occurred. Data class: Non-PII.'
    """)
    
    op.execute("""
        COMMENT ON COLUMN channel_state_transitions.reason IS 
            'Human-readable explanation for transition (optional but recommended). Data class: Non-PII.'
    """)
    
    op.execute("""
        COMMENT ON COLUMN channel_state_transitions.metadata IS 
            'Additional context (e.g., ticket reference, migration ID). Data class: Non-PII.'
    """)
    
    # Step 5: Log completion
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE 'channel_state_transitions table created';
            RAISE NOTICE 'Indexes added for chronological and state queries';
            RAISE NOTICE 'FK constraint links to channel_taxonomy';
        END $$;
    """)


def downgrade() -> None:
    """
    Drop channel_state_transitions audit table.
    
    WARNING: This rollback removes the audit trail for channel state changes.
    After this migration is rolled back, channel state transitions are unaudited.
    """
    
    # Drop table (CASCADE will drop indexes and constraints)
    op.execute("DROP TABLE IF EXISTS channel_state_transitions CASCADE")
    
    # Log rollback
    op.execute("""
        DO $$
        BEGIN
            RAISE WARNING 'channel_state_transitions table dropped';
            RAISE WARNING 'Channel state transition audit trail removed';
        END $$;
    """)




