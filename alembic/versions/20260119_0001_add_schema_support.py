"""Add schema support for DID-based multi-tenancy.

Revision ID: 20260119_0001
Revises: 20251207_0905_ef0d61440935
Create Date: 2026-01-19 21:17:00.000000

This migration adds support for creating tables within DID-specific schemas
for multi-tenant isolation. Each DID gets its own PostgreSQL schema containing
all tables (tasks, contexts, task_feedback, webhook_configs).

This migration does NOT automatically create schemas - schemas are created
on-demand when an agent with a DID connects. This migration provides the
helper functions to support that workflow.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260119_0001"
down_revision: Union[str, None] = "20250614_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add schema management support.

    This migration creates a helper function that can be used to create
    all tables in a specific schema for a DID.
    """
    # Create a stored procedure to create all tables in a given schema
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

            RAISE NOTICE 'Created all Bindu tables in schema: %', schema_name;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create a helper function to drop all tables in a schema
    op.execute("""
        CREATE OR REPLACE FUNCTION drop_bindu_tables_in_schema(schema_name TEXT)
        RETURNS VOID AS $$
        BEGIN
            EXECUTE format('DROP TABLE IF EXISTS %I.task_feedback CASCADE', schema_name);
            EXECUTE format('DROP TABLE IF EXISTS %I.webhook_configs CASCADE', schema_name);
            EXECUTE format('DROP TABLE IF EXISTS %I.tasks CASCADE', schema_name);
            EXECUTE format('DROP TABLE IF EXISTS %I.contexts CASCADE', schema_name);

            RAISE NOTICE 'Dropped all Bindu tables in schema: %', schema_name;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Add a comment explaining the schema-based approach
    op.execute("""
        COMMENT ON FUNCTION create_bindu_tables_in_schema(TEXT) IS
        'Creates all Bindu tables (tasks, contexts, task_feedback, webhook_configs) in the specified schema for DID-based multi-tenancy isolation';
    """)

    op.execute("""
        COMMENT ON FUNCTION drop_bindu_tables_in_schema(TEXT) IS
        'Drops all Bindu tables from the specified schema';
    """)


def downgrade() -> None:
    """Downgrade database schema - remove schema management functions."""
    op.execute("DROP FUNCTION IF EXISTS create_bindu_tables_in_schema(TEXT)")
    op.execute("DROP FUNCTION IF EXISTS drop_bindu_tables_in_schema(TEXT)")
