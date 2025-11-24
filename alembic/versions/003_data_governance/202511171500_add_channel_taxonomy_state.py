"""Add state column to channel_taxonomy table

Revision ID: 202511171500
Revises: 202511171400
Create Date: 2025-11-17 15:00:00.000000

Phase 4 of Channel Governance Auditability Implementation

This migration adds the state column to channel_taxonomy to enable
state machine lifecycle management:
1. Adds state VARCHAR(50) column with CHECK constraint
2. Sets default value 'active' for existing rows
3. Backfills all existing channels to 'active' state

This migration is BLOCKING for:
- Channel state machine implementation
- Channel auditability system

Exit Gates:
- Migration applies cleanly
- All existing channels have state = 'active'
- CHECK constraint enforces valid states
"""

from alembic import op
import sqlalchemy as sa
from typing import Union


# revision identifiers, used by Alembic.
revision: str = '202511171500'
down_revision: Union[str, None] = '202511171400'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """
    Add state column to channel_taxonomy with CHECK constraint.
    
    Implementation:
    1. Add state column with DEFAULT 'active' and CHECK constraint
    2. Backfill existing rows to 'active' state (safety net)
    3. Update column comment
    """
    
    # Step 1: Add state column with CHECK constraint
    op.execute("""
        ALTER TABLE channel_taxonomy
        ADD COLUMN state VARCHAR(50) NOT NULL DEFAULT 'active'
        CHECK (state IN ('draft', 'active', 'deprecated', 'archived'))
    """)
    
    # Step 2: Backfill existing rows (safety net - DEFAULT should handle this)
    # This ensures any NULL values (shouldn't exist) are set to 'active'
    op.execute("""
        UPDATE channel_taxonomy
        SET state = 'active'
        WHERE state IS NULL
    """)
    
    # Step 3: Update column comment
    op.execute("""
        COMMENT ON COLUMN channel_taxonomy.state IS 
            'Channel lifecycle state: draft (testing), active (production), deprecated (soft retirement), archived (hard retirement). Purpose: Enable state machine governance and auditability. Data class: Non-PII.'
    """)
    
    # Step 4: Log completion
    op.execute("""
        DO $$
        BEGIN
            RAISE NOTICE 'State column added to channel_taxonomy';
            RAISE NOTICE 'All existing channels set to ''active'' state';
            RAISE NOTICE 'CHECK constraint enforces valid states: draft, active, deprecated, archived';
        END $$;
    """)


def downgrade() -> None:
    """
    Remove state column from channel_taxonomy.
    
    WARNING: This rollback removes state machine lifecycle management.
    After this migration is rolled back, channels cannot be deprecated/archived.
    """
    
    # Drop state column (CASCADE will drop any dependent constraints)
    op.execute("ALTER TABLE channel_taxonomy DROP COLUMN IF EXISTS state")
    
    # Log rollback
    op.execute("""
        DO $$
        BEGIN
            RAISE WARNING 'State column removed from channel_taxonomy';
            RAISE WARNING 'Channel state machine lifecycle management disabled';
        END $$;
    """)




