"""Initial schema for Bindu storage.

Revision ID: 20251207_0001
Revises:
Create Date: 2025-12-07 10:03:00.000000

This migration creates the core tables for A2A protocol task and context management:
- tasks: Stores task data with JSONB history and artifacts
- contexts: Stores conversation context with message history
- task_feedback: Stores optional user feedback for tasks
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251207_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - create initial tables."""
    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False, server_default="task"),
        sa.Column("state", sa.String(50), nullable=False),
        sa.Column("state_timestamp", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "artifacts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="[]",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        comment="A2A protocol tasks with JSONB history and artifacts",
    )

    # Create contexts table
    op.create_table(
        "contexts",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "context_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "message_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        comment="Conversation contexts with message history",
    )

    # Create task_feedback table
    op.create_table(
        "task_feedback",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "feedback_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        comment="User feedback for tasks",
    )

    # Create agent_prompts table
    # Define enum but don't create it separately - create_table will handle it
    prompt_status_enum = sa.Enum(
        "active",
        "candidate",
        "deprecated",
        "rolled_back",
        name="promptstatus"
    )

    op.create_table(
        "agent_prompts",
        sa.Column(
            "id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("status", prompt_status_enum, nullable=False),
        sa.Column("traffic", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0"),
        sa.Column("num_interactions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_feedback_score", sa.Numeric(precision=3, scale=2), nullable=True, server_default=None),
        sa.CheckConstraint("traffic >= 0 AND traffic <= 1", name="chk_agent_prompts_traffic_range"),
        sa.CheckConstraint("average_feedback_score IS NULL OR (average_feedback_score >= 0 AND average_feedback_score <= 1)", name="chk_agent_prompts_feedback_range"),
        comment="Prompts used by agents with constrained active/candidate counts",
    )

    # Enforce only one active and only one candidate via partial unique indexes
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

    # Create indexes for performance

    # Tasks indexes
    op.create_index("idx_tasks_context_id", "tasks", ["context_id"])
    op.create_index("idx_tasks_state", "tasks", ["state"])
    op.create_index(
        "idx_tasks_created_at",
        "tasks",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "idx_tasks_updated_at",
        "tasks",
        ["updated_at"],
        postgresql_ops={"updated_at": "DESC"},
    )

    # GIN indexes for JSONB columns (for efficient querying inside JSON)
    op.create_index(
        "idx_tasks_history_gin", "tasks", ["history"], postgresql_using="gin"
    )
    op.create_index(
        "idx_tasks_metadata_gin", "tasks", ["metadata"], postgresql_using="gin"
    )
    op.create_index(
        "idx_tasks_artifacts_gin", "tasks", ["artifacts"], postgresql_using="gin"
    )

    # Contexts indexes
    op.create_index(
        "idx_contexts_created_at",
        "contexts",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "idx_contexts_updated_at",
        "contexts",
        ["updated_at"],
        postgresql_ops={"updated_at": "DESC"},
    )
    op.create_index(
        "idx_contexts_data_gin", "contexts", ["context_data"], postgresql_using="gin"
    )
    op.create_index(
        "idx_contexts_history_gin",
        "contexts",
        ["message_history"],
        postgresql_using="gin",
    )

    # Task feedback indexes
    op.create_index("idx_task_feedback_task_id", "task_feedback", ["task_id"])
    op.create_index(
        "idx_task_feedback_created_at",
        "task_feedback",
        ["created_at"],
        postgresql_ops={"created_at": "DESC"},
    )

    # Create trigger function for updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create triggers for automatic updated_at updates
    op.execute("""
        CREATE TRIGGER update_tasks_updated_at
        BEFORE UPDATE ON tasks
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_contexts_updated_at
        BEFORE UPDATE ON contexts
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Downgrade database schema - drop all tables and functions."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_contexts_updated_at ON contexts")
    op.execute("DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop indexes (will be dropped automatically with tables, but explicit for clarity)
    op.drop_index("idx_task_feedback_created_at", table_name="task_feedback")
    op.drop_index("idx_task_feedback_task_id", table_name="task_feedback")

    op.drop_index("idx_contexts_history_gin", table_name="contexts")
    op.drop_index("idx_contexts_data_gin", table_name="contexts")
    op.drop_index("idx_contexts_updated_at", table_name="contexts")
    op.drop_index("idx_contexts_created_at", table_name="contexts")

    op.drop_index("idx_tasks_artifacts_gin", table_name="tasks")
    op.drop_index("idx_tasks_metadata_gin", table_name="tasks")
    op.drop_index("idx_tasks_history_gin", table_name="tasks")
    op.drop_index("idx_tasks_updated_at", table_name="tasks")
    op.drop_index("idx_tasks_created_at", table_name="tasks")
    op.drop_index("idx_tasks_state", table_name="tasks")
    op.drop_index("idx_tasks_context_id", table_name="tasks")

    # Drop agent_prompts indexes and table
    op.drop_index("uq_agent_prompts_status_candidate", table_name="agent_prompts")
    op.drop_index("uq_agent_prompts_status_active", table_name="agent_prompts")
    op.drop_table("agent_prompts")
    # Drop enum type used for status
    op.execute("DROP TYPE IF EXISTS promptstatus")

    # Drop tables
    op.drop_table("task_feedback")
    op.drop_table("contexts")
    op.drop_table("tasks")
