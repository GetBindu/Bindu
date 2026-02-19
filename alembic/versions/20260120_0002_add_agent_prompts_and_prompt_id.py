"""Add prompt_id to tasks.

Revision ID: 20260120_0002
Revises: 20260119_0001
Create Date: 2026-01-20 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260120_0002"
down_revision: Union[str, None] = "20260119_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------
    # 1️⃣ Add prompt_id column to tasks (String/UUID)
    # -----------------------------------------------------
    op.add_column(
        "tasks",
        sa.Column("prompt_id", sa.String(), nullable=True),
    )

    # -----------------------------------------------------
    # 2️⃣ Index for performance
    # -----------------------------------------------------
    op.create_index(
        "idx_tasks_prompt_id",
        "tasks",
        ["prompt_id"],
    )


def downgrade() -> None:
    # -----------------------------------------------------
    # Reverse order matters
    # -----------------------------------------------------

    op.drop_index("idx_tasks_prompt_id", table_name="tasks")
    op.drop_column("tasks", "prompt_id")
