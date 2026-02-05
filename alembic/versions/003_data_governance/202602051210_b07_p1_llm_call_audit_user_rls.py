"""Add user scoping and RLS to llm_call_audit

Revision ID: 202602051210
Revises: 202601031930
Create Date: 2026-02-05 12:10:00

Migration Description:
Adds user_id to llm_call_audit and enforces tenant+user RLS policies.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "202602051210"
down_revision: Union[str, None] = "202601031930"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    op.execute(
        f"ALTER TABLE llm_call_audit ADD COLUMN user_id UUID NOT NULL DEFAULT '{SYSTEM_USER_ID}'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_call_audit_tenant_user_created "
        "ON llm_call_audit(tenant_id, user_id, created_at DESC)"
    )

    op.execute("ALTER TABLE llm_call_audit ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE llm_call_audit FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON llm_call_audit")
    op.execute(
        """
        CREATE POLICY tenant_isolation_policy ON llm_call_audit
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
    op.execute(
        """
        COMMENT ON POLICY tenant_isolation_policy ON llm_call_audit IS
            'RLS policy enforcing tenant + user isolation. Requires app.current_tenant_id and app.current_user_id.'
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON llm_call_audit")
    op.execute("ALTER TABLE llm_call_audit DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS idx_llm_call_audit_tenant_user_created")
    op.execute("ALTER TABLE llm_call_audit DROP COLUMN IF EXISTS user_id")
