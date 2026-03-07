"""Add task_checkpoints table for pause/resume support.

Revision ID: 20260306_0001
Revises: 20260119_0001
Create Date: 2026-03-06 00:00:00.000000

This migration adds the task_checkpoints table to store execution state
for pause/resume functionality. Checkpoints allow tasks to be suspended
and resumed later from the same point.

The checkpoint stores:
- checkpoint_data: JSONB containing execution state
- step_number: Current step in execution
- step_label: Optional label for the current step
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260306_0001"
down_revision: Union[str, None] = "20260119_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add task_checkpoints table."""
    op.create_table(
        "task_checkpoints",
        op.Column(
            "id", op.Integer(), primary_key=True, autoincrement=True, nullable=False
        ),
        op.Column("task_id", op.UUID(as_uuid=True), nullable=False),
        op.Column("checkpoint_data", op.JSONB(), nullable=False),
        op.Column("step_number", op.Integer(), nullable=False, server_default="0"),
        op.Column("step_label", op.String(255), nullable=True),
        op.Column(
            "created_at",
            op.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=op.text("NOW()"),
        ),
        op.Column(
            "updated_at",
            op.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=op.text("NOW()"),
        ),
    )

    op.create_index("idx_task_checkpoints_task_id", "task_checkpoints", ["task_id"])
    op.create_index(
        "idx_task_checkpoints_created_at", "task_checkpoints", ["created_at"]
    )

    op.create_foreign_key(
        "fk_task_checkpoints_task",
        "task_checkpoints",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.alter_column("task_checkpoints", "task_id", nullable=False)

    # Update the helper function to include task_checkpoints table
    op.execute("""
        CREATE OR REPLACE FUNCTION create_bindu_tables_in_schema(schema_name TEXT)
        RETURNS VOID AS $$
        BEGIN
            -- Create tasks table
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I.tasks (
                    id UUID PRIMARY KEY NOT NULL,
                    context_id UUID NOT NULL,
                    kind VARCHAR(50) NOT NULL DEFAULT ''task'',
                    state VARCHAR(50) NOT NULL,
                    state_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    history JSONB NOT NULL DEFAULT ''[]''::jsonb,
                    artifacts JSONB DEFAULT ''[]''::jsonb,
                    metadata JSONB DEFAULT ''{}''::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    CONSTRAINT fk_tasks_context FOREIGN KEY (context_id)
                        REFERENCES %I.contexts(id) ON DELETE CASCADE
                )', schema_name, schema_name);

            -- Create contexts table
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I.contexts (
                    id UUID PRIMARY KEY NOT NULL,
                    context_data JSONB NOT NULL DEFAULT ''{}''::jsonb,
                    message_history JSONB DEFAULT ''[]''::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )', schema_name);

            -- Create task_feedback table
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I.task_feedback (
                    id SERIAL PRIMARY KEY NOT NULL,
                    task_id UUID NOT NULL,
                    feedback_data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    CONSTRAINT fk_task_feedback_task FOREIGN KEY (task_id)
                        REFERENCES %I.tasks(id) ON DELETE CASCADE
                )', schema_name, schema_name);

            -- Create webhook_configs table
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I.webhook_configs (
                    task_id UUID PRIMARY KEY NOT NULL,
                    config JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    CONSTRAINT fk_webhook_configs_task FOREIGN KEY (task_id)
                        REFERENCES %I.tasks(id) ON DELETE CASCADE
                )', schema_name, schema_name);

            -- Create task_checkpoints table
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I.task_checkpoints (
                    id SERIAL PRIMARY KEY NOT NULL,
                    task_id UUID NOT NULL,
                    checkpoint_data JSONB NOT NULL,
                    step_number INTEGER NOT NULL DEFAULT 0,
                    step_label VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    CONSTRAINT fk_task_checkpoints_task FOREIGN KEY (task_id)
                        REFERENCES %I.tasks(id) ON DELETE CASCADE
                )', schema_name, schema_name);

            -- Create indexes for tasks
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_tasks_context_id ON %I.tasks(context_id)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_tasks_state ON %I.tasks(state)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON %I.tasks(created_at DESC)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON %I.tasks(updated_at DESC)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_tasks_history_gin ON %I.tasks USING gin(history)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_tasks_metadata_gin ON %I.tasks USING gin(metadata)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_tasks_artifacts_gin ON %I.tasks USING gin(artifacts)', schema_name);

            -- Create indexes for contexts
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON %I.contexts(created_at DESC)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_updated_at ON %I.contexts(updated_at DESC)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_data_gin ON %I.contexts USING gin(context_data)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_history_gin ON %I.contexts USING gin(message_history)', schema_name);

            -- Create indexes for task_feedback
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_task_feedback_task_id ON %I.task_feedback(task_id)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_task_feedback_created_at ON %I.task_feedback(created_at DESC)', schema_name);

            -- Create indexes for webhook_configs
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_webhook_configs_created_at ON %I.webhook_configs(created_at DESC)', schema_name);

            -- Create indexes for task_checkpoints
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_task_checkpoints_task_id ON %I.task_checkpoints(task_id)', schema_name);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_task_checkpoints_created_at ON %I.task_checkpoints(created_at DESC)', schema_name);

            -- Create triggers for updated_at
            EXECUTE format('
                CREATE TRIGGER update_tasks_updated_at
                BEFORE UPDATE ON %I.tasks
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
            ', schema_name);

            EXECUTE format('
                CREATE TRIGGER update_contexts_updated_at
                BEFORE UPDATE ON %I.contexts
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
            ', schema_name);

            EXECUTE format('
                CREATE TRIGGER update_webhook_configs_updated_at
                BEFORE UPDATE ON %I.webhook_configs
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
            ', schema_name);

            EXECUTE format('
                CREATE TRIGGER update_task_checkpoints_updated_at
                BEFORE UPDATE ON %I.task_checkpoints
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
            ', schema_name);

            RAISE NOTICE 'Created all Bindu tables in schema: %', schema_name;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Update drop function to include task_checkpoints
    op.execute("""
        CREATE OR REPLACE FUNCTION drop_bindu_tables_in_schema(schema_name TEXT)
        RETURNS VOID AS $$
        BEGIN
            EXECUTE format('DROP TABLE IF EXISTS %I.task_checkpoints CASCADE', schema_name);
            EXECUTE format('DROP TABLE IF EXISTS %I.task_feedback CASCADE', schema_name);
            EXECUTE format('DROP TABLE IF EXISTS %I.webhook_configs CASCADE', schema_name);
            EXECUTE format('DROP TABLE IF EXISTS %I.tasks CASCADE', schema_name);
            EXECUTE format('DROP TABLE IF EXISTS %I.contexts CASCADE', schema_name);

            RAISE NOTICE 'Dropped all Bindu tables in schema: %', schema_name;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """Remove task_checkpoints table."""
    op.drop_table("task_checkpoints")
