"""Add agent_prompts table and prompt_id to tasks.

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
    # 1️⃣ Add prompt_id column to tasks
    # -----------------------------------------------------
    op.add_column(
        "tasks",
        sa.Column("prompt_id", sa.Integer(), nullable=True),
    )

    # -----------------------------------------------------
    # 2️⃣ Define enum type (DO NOT manually create it)
    # -----------------------------------------------------
    prompt_status_enum = sa.Enum(
        "active",
        "candidate",
        "deprecated",
        "rolled_back",
        name="promptstatus",
    )

    # -----------------------------------------------------
    # 3️⃣ Create agent_prompts table
    # (Enum will be automatically created by SQLAlchemy)
    # -----------------------------------------------------
    op.create_table(
        "agent_prompts",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("status", prompt_status_enum, nullable=False),
        sa.Column(
            "traffic",
            sa.Numeric(precision=5, scale=4),
            nullable=False,
            server_default="0",
        ),
        sa.CheckConstraint(
            "traffic >= 0 AND traffic <= 1",
            name="chk_agent_prompts_traffic_range",
        ),
        comment="Prompts used by agents with constrained active/candidate counts",
    )

    # -----------------------------------------------------
    # 4️⃣ Partial unique indexes
    # -----------------------------------------------------
    op.create_index(
        "uq_agent_prompts_status_active",
        "agent_prompts",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_index(
        "uq_agent_prompts_status_candidate",
        "agent_prompts",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'candidate'"),
    )

    # -----------------------------------------------------
    # 5️⃣ Foreign key from tasks → agent_prompts
    # -----------------------------------------------------
    op.create_foreign_key(
        "fk_tasks_prompt_id",
        "tasks",
        "agent_prompts",
        ["prompt_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -----------------------------------------------------
    # 6️⃣ Index for performance
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

    op.drop_constraint("fk_tasks_prompt_id", "tasks", type_="foreignkey")

    op.drop_index("uq_agent_prompts_status_candidate", table_name="agent_prompts")
    op.drop_index("uq_agent_prompts_status_active", table_name="agent_prompts")

    op.drop_table("agent_prompts")

    # Explicitly drop enum type
    op.execute("DROP TYPE IF EXISTS promptstatus")

    op.drop_column("tasks", "prompt_id")