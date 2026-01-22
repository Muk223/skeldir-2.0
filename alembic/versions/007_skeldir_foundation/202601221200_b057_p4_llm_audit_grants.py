"""Grant runtime roles access to LLM audit tables (B0.5.7-P4).

Revision ID: 202601221200
Revises: 202601211900
Create Date: 2026-01-22 12:00:00

Migration Description:
Adds least-privilege GRANTs for runtime roles on LLM audit tables required by
deterministic stubs. This enables app_user (via app_rw membership) to persist
audit rows while preserving RLS tenant isolation.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "202601221200"
down_revision: Union[str, None] = "202601211900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LLM_AUDIT_GRANTS = {
    "llm_api_calls": ["SELECT", "INSERT"],
    "llm_monthly_costs": ["SELECT", "INSERT", "UPDATE"],
    "investigations": ["SELECT", "INSERT"],
    "budget_optimization_jobs": ["SELECT", "INSERT"],
}


def upgrade() -> None:
    for table_name, privileges in LLM_AUDIT_GRANTS.items():
        grants = ", ".join(privileges)
        op.execute(f"GRANT {grants} ON TABLE {table_name} TO app_rw")


def downgrade() -> None:
    for table_name in LLM_AUDIT_GRANTS.keys():
        op.execute(f"REVOKE ALL ON TABLE {table_name} FROM app_rw")
