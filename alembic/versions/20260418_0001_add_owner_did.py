"""Add owner_did to tasks and contexts for per-caller ownership tracking.

Revision ID: 20260418_0001
Revises: 20260119_0001
Create Date: 2026-04-18 14:00:00.000000

Adds a nullable ``owner_did`` column + index to the ``tasks`` and ``contexts``
tables. Populated from the authenticated caller's ``client_id`` on first write
(``submit_task``). Used by Phase 2 of the IDOR fix to filter reads/writes so a
caller can only see their own tasks and contexts.

Nullable because:
  1. Requests made with auth disabled have no caller identity.
  2. Rows that existed before this migration have no owner until backfilled.

Rows with NULL ``owner_did`` remain accessible only to unauthenticated callers
(``caller_did=None``) once enforcement lands, preserving today's dev-mode
behavior.

This migration only touches the global ``public.tasks`` and ``public.contexts``
tables. Operators running the per-DID schema feature added in
``20260119_0001_add_schema_support`` must alter existing DID-specific schemas
manually; the ``create_bindu_tables_in_schema`` helper is updated in a follow-up
so that newly-created DID schemas pick up the column automatically.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_0001"
down_revision: Union[str, None] = "20260119_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add owner_did column + index to tasks and contexts."""
    op.add_column(
        "tasks",
        sa.Column("owner_did", sa.String(length=255), nullable=True),
    )
    op.create_index("idx_tasks_owner_did", "tasks", ["owner_did"])

    op.add_column(
        "contexts",
        sa.Column("owner_did", sa.String(length=255), nullable=True),
    )
    op.create_index("idx_contexts_owner_did", "contexts", ["owner_did"])


def downgrade() -> None:
    """Remove owner_did column + index from tasks and contexts."""
    op.drop_index("idx_contexts_owner_did", table_name="contexts")
    op.drop_column("contexts", "owner_did")

    op.drop_index("idx_tasks_owner_did", table_name="tasks")
    op.drop_column("tasks", "owner_did")
