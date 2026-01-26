"""PostgreSQL storage implementation using SQLAlchemy with imperative mapping.

This implementation provides a persistent storage backend suitable for:
- Production deployments
- Multi-pod/distributed systems
- Long-term data retention
- Enterprise environments

Hybrid Agent Pattern Support:
- Stores tasks with flexible state transitions (working → input-required → completed)
- Maintains conversation context across multiple tasks
- Supports incremental message history updates
- Enables task refinements through context-based task lookup
- Survives pod restarts and redeployments

Features:
- SQLAlchemy imperative mapping with protocol TypedDicts
- No duplicate ORM models - uses protocol types directly
- Connection pooling for performance
- Automatic retry logic for transient failures
- JSONB for efficient storage of A2A protocol objects
- Transaction support for data consistency
- Indexed queries for fast lookups
"""

from __future__ import annotations as _annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import delete, func, select, text, update, cast
from sqlalchemy.dialects.postgresql import insert, JSONB, JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing_extensions import TypeVar

from bindu.common.protocol.types import (
    Artifact,
    Message,
    PushNotificationConfig,
    Task,
    TaskState,
    TaskStatus,
)
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

from .base import Storage
from .helpers import (
    mask_database_url,
    normalize_message_uuids,
    normalize_uuid,
    sanitize_identifier,
    serialize_for_jsonb,
    validate_uuid_type,
)
from .helpers.db_operations import get_current_utc_timestamp
from .schema import (
    agent_prompts_table,
    contexts_table,
    task_feedback_table,
    tasks_table,
    webhook_configs_table,
)

logger = get_logger("bindu.server.storage.postgres_storage")

ContextT = TypeVar("ContextT", default=Any)


class PostgresStorage(Storage[ContextT]):
    """PostgreSQL storage implementation using SQLAlchemy imperative mapping.

    Storage Structure:
    - tasks_table: All tasks with JSONB history and artifacts
    - contexts_table: Context metadata and message history
    - task_feedback_table: Optional feedback storage

    Uses protocol TypedDicts directly - no ORM model classes needed.

    Connection Management:
    - Uses SQLAlchemy async engine with connection pool
    - Automatic reconnection on connection loss
    - Configurable pool size and timeouts
    """

    def __init__(
        self,
        database_url: str | None = None,
        pool_min: int | None = None,
        pool_max: int | None = None,
        timeout: int | None = None,
        command_timeout: int | None = None,
        did: str | None = None,
    ):
        """Initialize PostgreSQL storage with SQLAlchemy.

        Args:
            database_url: PostgreSQL connection URL (defaults to settings)
            pool_min: Minimum pool size (defaults to settings)
            pool_max: Maximum pool size (defaults to settings)
            timeout: Connection timeout in seconds (defaults to settings)
            command_timeout: Command timeout in seconds (defaults to settings)
            did: Decentralized Identifier for schema-based multi-tenancy isolation.
                If provided, all operations will be scoped to this DID's schema.
                If None, uses the 'public' schema (legacy behavior).
        """
        # Use database URL from settings or parameter
        db_url = database_url or app_settings.storage.postgres_url

        # Ensure asyncpg driver is specified
        if db_url is not None:
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif not db_url.startswith("postgresql+asyncpg://"):
                db_url = f"postgresql+asyncpg://{db_url}"

        self.database_url: str | None = db_url
        self.pool_min = pool_min or app_settings.storage.postgres_pool_min
        self.pool_max = pool_max or app_settings.storage.postgres_pool_max
        self.timeout = timeout or app_settings.storage.postgres_timeout
        self.command_timeout = (
            command_timeout or app_settings.storage.postgres_command_timeout
        )

        self._engine = None
        self._session_factory = None
        self.did = did
        self.schema_name: str | None = None

        # If DID is provided, compute the schema name
        if did:
            from bindu.utils.schema_manager import sanitize_did_for_schema

            self.schema_name = sanitize_did_for_schema(did)
            logger.info(
                f"PostgresStorage configured for DID '{did}' using schema '{self.schema_name}'"
            )

    async def connect(self) -> None:
        """Initialize SQLAlchemy engine and session factory.

        Raises:
            ConnectionError: If unable to connect to database
        """
        try:
            masked_url = mask_database_url(self.database_url)
            logger.info("Connecting to PostgreSQL database with SQLAlchemy...")

            # Create async engine
            self._engine = create_async_engine(
                self.database_url,
                pool_size=self.pool_max,
                max_overflow=0,
                pool_timeout=self.timeout,
                pool_pre_ping=True,  # Verify connections before using
                echo=False,  # Set to True for SQL query logging
            )

            # Set up event listener to set search_path for DID schema
            if self.schema_name:
                from sqlalchemy import event

                sanitized_schema = sanitize_identifier(self.schema_name)

                @event.listens_for(self._engine.sync_engine, "connect")
                def set_search_path(dbapi_conn, connection_record):
                    cursor = dbapi_conn.cursor()
                    cursor.execute(f'SET search_path TO "{sanitized_schema}"')
                    cursor.close()

            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # If DID is provided, initialize the schema (this also tests the connection)
            if self.did and self.schema_name:
                from bindu.utils.schema_manager import initialize_did_schema

                logger.info(
                    f"Initializing schema '{self.schema_name}' for DID '{self.did}'..."
                )
                await initialize_did_schema(
                    self._engine, self.schema_name, create_tables=True
                )
                logger.info(f"Schema '{self.schema_name}' initialized successfully")
            else:
                # Test connection if no DID schema initialization
                async with self._engine.begin() as conn:
                    await conn.execute(select(1))

            logger.info(
                f"PostgreSQL storage connected to {masked_url} (pool_size={self.pool_max})"
                + (f" using schema '{self.schema_name}'" if self.schema_name else "")
            )

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e

    async def disconnect(self) -> None:
        """Close SQLAlchemy engine and connection pool."""
        if self._engine:
            await self._engine.dispose()
            logger.info("PostgreSQL connection pool closed")
            self._engine = None
            self._session_factory = None

    def _ensure_connected(self) -> None:
        """Ensure engine is initialized.

        Raises:
            RuntimeError: If engine is not initialized
        """
        if self._engine is None or self._session_factory is None:
            raise RuntimeError(
                "PostgreSQL engine not initialized. Call connect() first."
            )

    @asynccontextmanager
    async def _get_session_with_schema(self):
        """Create a session and set search_path for the DID's schema.

        This ensures all queries within the session use the DID's schema
        without needing to qualify table names. The search_path is set
        per-connection to avoid issues with connection pooling and reuse.

        Returns:
            AsyncSession context manager
        """
        try:
            async with self._session_factory() as session:
                # Set search_path for this session if we have a schema
                if self.schema_name:
                    sanitized_schema = sanitize_identifier(self.schema_name)
                    # Execute SET statement - this will auto-begin a transaction
                    await session.execute(
                        text(f'SET search_path TO "{sanitized_schema}"')
                    )
                    # Commit the transaction from the SET command
                    # This leaves the session clean for the caller to begin their own transaction
                    await session.commit()
                yield session
        except Exception as e:
            logger.error(
                f"Database session error: {type(e).__name__}: {e}",
                exc_info=True,
                extra={"schema": self.schema_name if hasattr(self, 'schema_name') else None}
            )
            raise

    async def _retry_on_connection_error(self, func, *args, **kwargs):
        """Retry function on connection errors using Tenacity.

        Args:
            func: Async function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            Exception: If all retries fail
        """
        # Use Tenacity-based retry with storage configuration
        from bindu.utils.retry import execute_with_retry

        max_retries = app_settings.storage.postgres_max_retries
        retry_delay = app_settings.storage.postgres_retry_delay

        return await execute_with_retry(
            func,
            *args,
            max_attempts=max_retries,
            min_wait=retry_delay,
            max_wait=retry_delay * max_retries,
            **kwargs,
        )

    def _row_to_task(self, row) -> Task:
        """Convert database row to Task protocol type.

        Args:
            row: SQLAlchemy Row object

        Returns:
            Task TypedDict from protocol
        """
        task = Task(
            id=row.id,
            context_id=row.context_id,
            kind=row.kind,
            status=TaskStatus(
                state=row.state, timestamp=row.state_timestamp.isoformat()
            ),
            history=row.history or [],
            artifacts=row.artifacts or [],
            metadata=row.metadata or {},
        )
        # Add prompt_id if present
        if hasattr(row, 'prompt_id') and row.prompt_id is not None:
            task["prompt_id"] = row.prompt_id
        return task

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    async def load_task(
        self, task_id: UUID, history_length: int | None = None
    ) -> Task | None:
        """Load a task from PostgreSQL using SQLAlchemy.

        Args:
            task_id: Unique identifier of the task
            history_length: Optional limit on message history length

        Returns:
            Task object if found, None otherwise

        Raises:
            TypeError: If task_id is not UUID
        """
        task_id = validate_uuid_type(task_id, "task_id")

        self._ensure_connected()

        async def _load():
            async with self._get_session_with_schema() as session:
                stmt = select(tasks_table).where(tasks_table.c.id == task_id)
                result = await session.execute(stmt)
                row = result.first()

                if row is None:
                    return None

                task = self._row_to_task(row)

                # Limit history if requested
                if history_length is not None and history_length > 0:
                    task["history"] = task["history"][-history_length:]

                return task

        return await self._retry_on_connection_error(_load)

    async def submit_task(self, context_id: UUID, message: Message) -> Task:
        """Create a new task or continue an existing non-terminal task.

        Task-First Pattern (Bindu):
        - If task exists and is in non-terminal state: Append message and reset to 'submitted'
        - If task exists and is in terminal state: Raise error (immutable)
        - If task doesn't exist: Create new task

        Args:
            context_id: Context to associate the task with
            message: Initial message containing task request

        Returns:
            Task in 'submitted' state (new or continued)

        Raises:
            TypeError: If IDs are invalid types
            ValueError: If attempting to continue a terminal task
        """
        context_id = validate_uuid_type(context_id, "context_id")
        task_id = normalize_uuid(message.get("task_id"), "task_id")
        message = normalize_message_uuids(
            message, task_id=task_id, context_id=context_id
        )

        self._ensure_connected()

        async def _submit():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    # Check if task exists
                    stmt = select(tasks_table).where(tasks_table.c.id == task_id)
                    result = await session.execute(stmt)
                    existing = result.first()

                    if existing:
                        # Task exists - check if mutable
                        current_state = existing.state

                        if current_state in app_settings.agent.terminal_states:
                            raise ValueError(
                                f"Cannot continue task {task_id}: Task is in terminal state '{current_state}' and is immutable. "
                                f"Create a new task with referenceTaskIds to continue the conversation."
                            )

                        logger.info(
                            f"Continuing existing task {task_id} from state '{current_state}'"
                        )

                        serialized_message = serialize_for_jsonb(message)
                        stmt = (
                            update(tasks_table)
                            .where(tasks_table.c.id == task_id)
                            .values(
                                history=func.jsonb_concat(
                                    tasks_table.c.history,
                                    cast([serialized_message], JSONB),
                                ),
                                state="submitted",
                                state_timestamp=get_current_utc_timestamp(),
                                updated_at=get_current_utc_timestamp(),
                            )
                            .returning(tasks_table)
                        )
                        result = await session.execute(stmt)
                        updated_row = result.first()

                        return self._row_to_task(updated_row)

                    # Ensure context exists BEFORE creating task (foreign key constraint)
                    stmt = insert(contexts_table).values(
                        id=context_id,
                        context_data={},
                        message_history=[],
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                    await session.execute(stmt)

                    serialized_message = serialize_for_jsonb(message)
                    now = get_current_utc_timestamp()
                    stmt = (
                        insert(tasks_table)
                        .values(
                            id=task_id,
                            context_id=context_id,
                            kind="task",
                            state="submitted",
                            state_timestamp=now,
                            history=[serialized_message],
                            artifacts=[],
                            metadata={},
                        )
                        .returning(tasks_table)
                    )
                    result = await session.execute(stmt)
                    new_row = result.first()

                    return self._row_to_task(new_row)

        return await self._retry_on_connection_error(_submit)

    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
        metadata: dict[str, Any] | None = None,
        prompt_id: int | None = None,
    ) -> Task:
        """Update task state and append new content using SQLAlchemy.

        Args:
            task_id: Task to update
            state: New task state
            new_artifacts: Optional artifacts to append
            new_messages: Optional messages to append to history
            metadata: Optional metadata to update/merge
            prompt_id: Optional prompt ID to associate with this task

        Returns:
            Updated task object

        Raises:
            TypeError: If task_id is not UUID
            KeyError: If task not found
        """
        task_id = validate_uuid_type(task_id, "task_id")

        self._ensure_connected()

        async def _update():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    # Check if task exists
                    stmt = select(tasks_table).where(tasks_table.c.id == task_id)
                    result = await session.execute(stmt)
                    task_row = result.first()

                    if task_row is None:
                        raise KeyError(f"Task {task_id} not found")

                    now = get_current_utc_timestamp()
                    update_values = {
                        "state": state,
                        "state_timestamp": now,
                        "updated_at": now,
                    }

                    if prompt_id is not None:
                        update_values["prompt_id"] = prompt_id

                    if metadata:
                        serialized_metadata = serialize_for_jsonb(metadata)
                        update_values["metadata"] = func.jsonb_concat(
                            tasks_table.c.metadata, cast(serialized_metadata, JSONB)
                        )

                    if new_artifacts:
                        serialized_artifacts = serialize_for_jsonb(new_artifacts)
                        update_values["artifacts"] = func.jsonb_concat(
                            tasks_table.c.artifacts, cast(serialized_artifacts, JSONB)
                        )

                    if new_messages:
                        for message in new_messages:
                            if not isinstance(message, dict):
                                raise TypeError(
                                    f"Message must be dict, got {type(message).__name__}"
                                )
                            normalize_message_uuids(
                                message, task_id=task_id, context_id=task_row.context_id
                            )

                        serialized_messages = serialize_for_jsonb(new_messages)
                        update_values["history"] = func.jsonb_concat(
                            tasks_table.c.history, cast(serialized_messages, JSONB)
                        )

                    # Execute update
                    stmt = (
                        update(tasks_table)
                        .where(tasks_table.c.id == task_id)
                        .values(**update_values)
                        .returning(tasks_table)
                    )
                    result = await session.execute(stmt)
                    updated_row = result.first()

                    return self._row_to_task(updated_row)

        return await self._retry_on_connection_error(_update)

    async def list_tasks(self, length: int | None = None) -> list[Task]:
        """List all tasks using SQLAlchemy.

        Args:
            length: Optional limit on number of tasks to return

        Returns:
            List of tasks
        """
        self._ensure_connected()

        async def _list():
            async with self._get_session_with_schema() as session:
                stmt = select(tasks_table).order_by(tasks_table.c.created_at.desc())

                if length is not None:
                    stmt = stmt.limit(length)

                result = await session.execute(stmt)
                rows = result.fetchall()

                return [self._row_to_task(row) for row in rows]

        return await self._retry_on_connection_error(_list)

    async def list_tasks_by_context(
        self, context_id: UUID, length: int | None = None
    ) -> list[Task]:
        """List tasks belonging to a specific context.

        Args:
            context_id: Context to filter tasks by
            length: Optional limit on number of tasks to return

        Returns:
            List of tasks in the context

        Raises:
            TypeError: If context_id is not UUID
        """
        context_id = validate_uuid_type(context_id, "context_id")

        self._ensure_connected()

        async def _list():
            async with self._get_session_with_schema() as session:
                stmt = (
                    select(tasks_table)
                    .where(tasks_table.c.context_id == context_id)
                    .order_by(tasks_table.c.created_at.asc())
                )

                if length is not None:
                    stmt = stmt.limit(length)

                result = await session.execute(stmt)
                rows = result.fetchall()

                return [self._row_to_task(row) for row in rows]

        return await self._retry_on_connection_error(_list)

    # -------------------------------------------------------------------------
    # Context Operations
    # -------------------------------------------------------------------------

    async def load_context(self, context_id: UUID) -> dict[str, Any] | None:
        """Load context from storage using SQLAlchemy.

        Args:
            context_id: Unique identifier of the context

        Returns:
            Context data if found, None otherwise

        Raises:
            TypeError: If context_id is not UUID
        """
        context_id = validate_uuid_type(context_id, "context_id")

        self._ensure_connected()

        async def _load():
            async with self._get_session_with_schema() as session:
                stmt = select(contexts_table).where(contexts_table.c.id == context_id)
                result = await session.execute(stmt)
                row = result.first()

                return row.context_data if row else None

        return await self._retry_on_connection_error(_load)

    async def update_context(self, context_id: UUID, context: ContextT) -> None:
        """Store or update context using SQLAlchemy.

        Args:
            context_id: Context identifier
            context: Context data

        Raises:
            TypeError: If context_id is not UUID
        """
        context_id = validate_uuid_type(context_id, "context_id")

        self._ensure_connected()

        async def _update():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    serialized_context = serialize_for_jsonb(
                        context if isinstance(context, dict) else {}
                    )
                    stmt = insert(contexts_table).values(
                        id=context_id,
                        context_data=serialized_context,
                        message_history=[],
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["id"],
                        set_={
                            "context_data": serialized_context,
                            "updated_at": get_current_utc_timestamp(),
                        },
                    )
                    await session.execute(stmt)

        await self._retry_on_connection_error(_update)

    async def append_to_contexts(
        self, context_id: UUID, messages: list[Message]
    ) -> None:
        """Append messages to context history using SQLAlchemy.

        Args:
            context_id: Context to update
            messages: Messages to append to history

        Raises:
            TypeError: If context_id is not UUID or messages is not a list
        """
        context_id = validate_uuid_type(context_id, "context_id")

        if not isinstance(messages, list):
            raise TypeError(f"messages must be list, got {type(messages).__name__}")

        self._ensure_connected()

        async def _append():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    # Ensure context exists
                    stmt = insert(contexts_table).values(
                        id=context_id,
                        context_data={},
                        message_history=[],
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                    await session.execute(stmt)

                    serialized_messages = serialize_for_jsonb(messages)
                    stmt = (
                        update(contexts_table)
                        .where(contexts_table.c.id == context_id)
                        .values(
                            message_history=func.jsonb_concat(
                                contexts_table.c.message_history,
                                cast(serialized_messages, JSONB),
                            ),
                            updated_at=get_current_utc_timestamp(),
                        )
                    )
                    await session.execute(stmt)

        await self._retry_on_connection_error(_append)

    async def list_contexts(self, length: int | None = None) -> list[dict[str, Any]]:
        """List all contexts using SQLAlchemy.

        Args:
            length: Optional limit on number of contexts to return

        Returns:
            List of context objects with task counts
        """
        self._ensure_connected()

        async def _list():
            async with self._get_session_with_schema() as session:
                # Query contexts with task counts
                stmt = (
                    select(
                        contexts_table.c.id.label("context_id"),
                        func.count(tasks_table.c.id).label("task_count"),
                        func.coalesce(
                            func.json_agg(tasks_table.c.id).filter(
                                tasks_table.c.id.isnot(None)
                            ),
                            cast("[]", JSON),
                        ).label("task_ids"),
                    )
                    .outerjoin(
                        tasks_table, contexts_table.c.id == tasks_table.c.context_id
                    )
                    .group_by(contexts_table.c.id)
                    .order_by(contexts_table.c.created_at.desc())
                )

                if length is not None:
                    stmt = stmt.limit(length)

                result = await session.execute(stmt)
                rows = result.fetchall()

                return [
                    {
                        "context_id": row.context_id,
                        "task_count": row.task_count,
                        "task_ids": row.task_ids,
                    }
                    for row in rows
                ]

        return await self._retry_on_connection_error(_list)

    # -------------------------------------------------------------------------
    # Utility Operations
    # -------------------------------------------------------------------------

    async def clear_context(self, context_id: UUID) -> None:
        """Clear all tasks associated with a specific context.

        Args:
            context_id: The context ID to clear

        Raises:
            TypeError: If context_id is not UUID
            ValueError: If context does not exist

        Warning: This is a destructive operation.
        """
        context_id = validate_uuid_type(context_id, "context_id")

        self._ensure_connected()

        async def _clear():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    # Check if context exists
                    stmt = select(contexts_table).where(
                        contexts_table.c.id == context_id
                    )
                    result = await session.execute(stmt)
                    context = result.first()

                    if context is None:
                        raise ValueError(f"Context {context_id} not found")

                    # Delete tasks (cascade will delete feedback)
                    stmt = delete(tasks_table).where(
                        tasks_table.c.context_id == context_id
                    )
                    result = await session.execute(stmt)
                    deleted_count = result.rowcount

                    # Delete context
                    stmt = delete(contexts_table).where(
                        contexts_table.c.id == context_id
                    )
                    await session.execute(stmt)

                    logger.info(
                        f"Cleared context {context_id}: removed {deleted_count} tasks"
                    )

        await self._retry_on_connection_error(_clear)

    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage.

        Warning: This is a destructive operation.
        """
        self._ensure_connected()

        async def _clear():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    await session.execute(delete(webhook_configs_table))
                    await session.execute(delete(task_feedback_table))
                    await session.execute(delete(tasks_table))
                    await session.execute(delete(contexts_table))
                    logger.info(
                        "Cleared all tasks, contexts, feedback, and webhook configs"
                    )

        await self._retry_on_connection_error(_clear)

    # -------------------------------------------------------------------------
    # Feedback Operations
    # -------------------------------------------------------------------------

    async def store_task_feedback(
        self, task_id: UUID, feedback_data: dict[str, Any]
    ) -> None:
        """Store user feedback for a task using SQLAlchemy.

        Args:
            task_id: Task to associate feedback with
            feedback_data: Feedback content

        Raises:
            TypeError: If task_id is not UUID or feedback_data is not dict
        """
        task_id = validate_uuid_type(task_id, "task_id")

        if not isinstance(feedback_data, dict):
            raise TypeError(
                f"feedback_data must be dict, got {type(feedback_data).__name__}"
            )

        self._ensure_connected()

        async def _store():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    serialized_feedback = serialize_for_jsonb(feedback_data)
                    stmt = insert(task_feedback_table).values(
                        task_id=task_id, feedback_data=serialized_feedback
                    )
                    await session.execute(stmt)

        await self._retry_on_connection_error(_store)

    async def get_task_feedback(self, task_id: UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task using SQLAlchemy.

        Args:
            task_id: Task to get feedback for

        Returns:
            List of feedback entries or None if no feedback exists

        Raises:
            TypeError: If task_id is not UUID
        """
        task_id = validate_uuid_type(task_id, "task_id")

        self._ensure_connected()

        async def _get():
            async with self._get_session_with_schema() as session:
                stmt = (
                    select(task_feedback_table)
                    .where(task_feedback_table.c.task_id == task_id)
                    .order_by(task_feedback_table.c.created_at.asc())
                )
                result = await session.execute(stmt)
                rows = result.fetchall()

                if not rows:
                    return None

                return [row.feedback_data for row in rows]

        return await self._retry_on_connection_error(_get)

    async def fetch_tasks_with_feedback(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch tasks with their associated feedback using LEFT JOIN.

        This method is optimized for DSPy training data extraction, providing
        task history along with feedback in a single efficient query.

        Args:
            limit: Maximum number of tasks to fetch (defaults to None for all tasks)

        Returns:
            List of dictionaries containing:
                - id: Task UUID
                - history: List of message dictionaries
                - created_at: Task creation timestamp
                - feedback_data: Optional feedback dictionary (None if no feedback)
        """
        self._ensure_connected()

        async def _fetch():
            async with self._get_session_with_schema() as session:
                # Query tasks with LEFT JOIN to feedback
                stmt = (
                    select(
                        tasks_table.c.id,
                        tasks_table.c.history,
                        tasks_table.c.created_at,
                        task_feedback_table.c.feedback_data,
                    )
                    .select_from(
                        tasks_table.outerjoin(
                            task_feedback_table,
                            tasks_table.c.id == task_feedback_table.c.task_id,
                        )
                    )
                    .order_by(tasks_table.c.created_at.desc())
                )

                if limit is not None:
                    stmt = stmt.limit(limit)

                result = await session.execute(stmt)
                rows = result.fetchall()

                return [
                    {
                        "id": row.id,
                        "history": row.history or [],
                        "created_at": row.created_at,
                        "feedback_data": row.feedback_data,
                    }
                    for row in rows
                ]

        return await self._retry_on_connection_error(_fetch)

    # -------------------------------------------------------------------------
    # Webhook Persistence Operations (for long-running tasks)
    # -------------------------------------------------------------------------

    async def save_webhook_config(
        self, task_id: UUID, config: PushNotificationConfig
    ) -> None:
        """Save a webhook configuration for a task using SQLAlchemy.

        Uses upsert to handle both insert and update scenarios.

        Args:
            task_id: Task to associate the webhook config with
            config: Push notification configuration to persist

        Raises:
            TypeError: If task_id is not UUID
        """
        task_id = validate_uuid_type(task_id, "task_id")

        self._ensure_connected()

        async def _save():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    serialized_config = serialize_for_jsonb(config)
                    stmt = insert(webhook_configs_table).values(
                        task_id=task_id,
                        config=serialized_config,
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["task_id"],
                        set_={
                            "config": serialized_config,
                            "updated_at": get_current_utc_timestamp(),
                        },
                    )
                    await session.execute(stmt)
                    logger.debug(f"Saved webhook config for task {task_id}")

        await self._retry_on_connection_error(_save)

    async def load_webhook_config(self, task_id: UUID) -> PushNotificationConfig | None:
        """Load a webhook configuration for a task using SQLAlchemy.

        Args:
            task_id: Task to load the webhook config for

        Returns:
            The webhook configuration if found, None otherwise

        Raises:
            TypeError: If task_id is not UUID
        """
        task_id = validate_uuid_type(task_id, "task_id")

        self._ensure_connected()

        async def _load():
            async with self._get_session_with_schema() as session:
                stmt = select(webhook_configs_table).where(
                    webhook_configs_table.c.task_id == task_id
                )
                result = await session.execute(stmt)
                row = result.first()

                if row is None:
                    return None

                return row.config

        return await self._retry_on_connection_error(_load)

    async def delete_webhook_config(self, task_id: UUID) -> None:
        """Delete a webhook configuration for a task using SQLAlchemy.

        Args:
            task_id: Task to delete the webhook config for

        Raises:
            TypeError: If task_id is not UUID

        Note: Does not raise if the config doesn't exist.
        """
        task_id = validate_uuid_type(task_id, "task_id")

        self._ensure_connected()

        async def _delete():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    stmt = delete(webhook_configs_table).where(
                        webhook_configs_table.c.task_id == task_id
                    )
                    result = await session.execute(stmt)
                    if result.rowcount > 0:
                        logger.debug(f"Deleted webhook config for task {task_id}")

        await self._retry_on_connection_error(_delete)

    async def load_all_webhook_configs(self) -> dict[UUID, PushNotificationConfig]:
        """Load all stored webhook configurations using SQLAlchemy.

        Used during initialization to restore webhook state after restart.

        Returns:
            Dictionary mapping task IDs to their webhook configurations
        """
        self._ensure_connected()

        async def _load_all():
            async with self._get_session_with_schema() as session:
                stmt = select(webhook_configs_table)
                result = await session.execute(stmt)
                rows = result.fetchall()

                return {row.task_id: row.config for row in rows}

        return await self._retry_on_connection_error(_load_all)
    # -------------------------------------------------------------------------
    # Prompt Management Operations (for DSPy A/B testing)
    # -------------------------------------------------------------------------

    async def get_active_prompt(self) -> dict[str, Any] | None:
        """Get the current active prompt with calculated metrics.

        Returns:
            Dictionary containing prompt data (id, prompt_text, status, traffic,
            num_interactions, average_feedback_score) or None if no active prompt exists.
            num_interactions and average_feedback_score are calculated on-demand from tasks table.
        """
        self._ensure_connected()

        async def _get():
            async with self._get_session_with_schema() as session:
                stmt = select(agent_prompts_table).where(
                    agent_prompts_table.c.status == "active"
                )
                result = await session.execute(stmt)
                row = result.fetchone()

                if row:
                    # Calculate metrics on-demand
                    metrics = await self._calculate_prompt_metrics(row.id, session)
                    
                    return {
                        "id": row.id,
                        "prompt_text": row.prompt_text,
                        "status": row.status,
                        "traffic": float(row.traffic) if row.traffic is not None else 0.0,
                        "num_interactions": metrics["num_interactions"],
                        "average_feedback_score": metrics["average_feedback_score"],
                    }

                return None

        return await self._retry_on_connection_error(_get)

    async def get_candidate_prompt(self) -> dict[str, Any] | None:
        """Get the current candidate prompt with calculated metrics.

        Returns:
            Dictionary containing prompt data (id, prompt_text, status, traffic,
            num_interactions, average_feedback_score) or None if no candidate prompt exists.
            num_interactions and average_feedback_score are calculated on-demand from tasks table.
        """
        self._ensure_connected()

        async def _get():
            async with self._get_session_with_schema() as session:
                stmt = select(agent_prompts_table).where(
                    agent_prompts_table.c.status == "candidate"
                )
                result = await session.execute(stmt)
                row = result.fetchone()

                if row:
                    # Calculate metrics on-demand
                    metrics = await self._calculate_prompt_metrics(row.id, session)
                    
                    return {
                        "id": row.id,
                        "prompt_text": row.prompt_text,
                        "status": row.status,
                        "traffic": float(row.traffic) if row.traffic is not None else 0.0,
                        "num_interactions": metrics["num_interactions"],
                        "average_feedback_score": metrics["average_feedback_score"],
                    }

                return None

        return await self._retry_on_connection_error(_get)

    async def insert_prompt(self, text: str, status: str, traffic: float) -> int:
        """Insert a new prompt into the database.

        Args:
            text: The prompt text content
            status: The prompt status (active, candidate, deprecated, rolled_back)
            traffic: Traffic allocation (0.0 to 1.0)

        Returns:
            The ID of the newly inserted prompt

        Raises:
            ValueError: If traffic is not in range [0, 1]
        """
        if not 0 <= traffic <= 1:
            raise ValueError(f"Traffic must be between 0 and 1, got {traffic}")

        self._ensure_connected()

        async def _insert():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    stmt = agent_prompts_table.insert().values(
                        prompt_text=text,
                        status=status,
                        traffic=traffic,
                    ).returning(agent_prompts_table.c.id)

                    result = await session.execute(stmt)
                    prompt_id = result.scalar_one()
                    logger.info(f"Inserted prompt {prompt_id} with status '{status}' and traffic {traffic}")
                    return prompt_id

        return await self._retry_on_connection_error(_insert)

    async def update_prompt_traffic(self, prompt_id: int, traffic: float) -> None:
        """Update the traffic allocation for a specific prompt.

        Args:
            prompt_id: The ID of the prompt to update
            traffic: New traffic allocation (0.0 to 1.0)

        Raises:
            ValueError: If traffic is not in range [0, 1]
        """
        if not 0 <= traffic <= 1:
            raise ValueError(f"Traffic must be between 0 and 1, got {traffic}")

        self._ensure_connected()

        async def _update():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    stmt = (
                        update(agent_prompts_table)
                        .where(agent_prompts_table.c.id == prompt_id)
                        .values(traffic=traffic)
                    )

                    await session.execute(stmt)
                    logger.info(f"Updated traffic for prompt {prompt_id} to {traffic}")

        await self._retry_on_connection_error(_update)

    async def update_prompt_status(self, prompt_id: int, status: str) -> None:
        """Update the status of a specific prompt.

        Args:
            prompt_id: The ID of the prompt to update
            status: New status (active, candidate, deprecated, rolled_back)
        """
        self._ensure_connected()

        async def _update():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    stmt = (
                        update(agent_prompts_table)
                        .where(agent_prompts_table.c.id == prompt_id)
                        .values(status=status)
                    )

                    await session.execute(stmt)
                    logger.info(f"Updated status for prompt {prompt_id} to '{status}'")

        await self._retry_on_connection_error(_update)

    async def zero_out_all_except(self, prompt_ids: list[int]) -> None:
        """Set traffic to 0 for all prompts except those in the given list.

        Args:
            prompt_ids: List of prompt IDs to preserve (keep their traffic unchanged)
        """
        self._ensure_connected()

        async def _zero():
            async with self._get_session_with_schema() as session:
                async with session.begin():
                    stmt = (
                        update(agent_prompts_table)
                        .where(agent_prompts_table.c.id.notin_(prompt_ids))
                        .values(traffic=0)
                    )

                    result = await session.execute(stmt)
                    logger.info(
                        f"Zeroed out traffic for {result.rowcount} prompts "
                        f"(preserving IDs: {prompt_ids})"
                    )

        await self._retry_on_connection_error(_zero)

    async def _calculate_prompt_metrics(
        self, prompt_id: int, session=None
    ) -> dict[str, Any]:
        """Calculate prompt metrics on-demand by querying tasks with this prompt_id.

        Args:
            prompt_id: ID of the prompt to calculate metrics for
            session: Optional existing session to reuse

        Returns:
            Dictionary with:
                - num_interactions: Total number of tasks that used this prompt
                - average_feedback_score: Average normalized feedback score (0-1) or None
        """
        # Helper to execute the query
        async def _calc(session):
            # Join tasks with task_feedback to get feedback scores
            # Count total tasks and calculate average feedback score
            stmt = (
                select(
                    func.count(tasks_table.c.id).label("num_interactions"),
                    func.avg(
                        cast(
                            func.jsonb_extract_path_text(
                                task_feedback_table.c.feedback_data, "rating"
                            ),
                            sa.Numeric
                        ) / 5.0  # Normalize 1-5 rating to 0-1
                    ).label("average_feedback_score")
                )
                .select_from(
                    tasks_table.outerjoin(
                        task_feedback_table,
                        tasks_table.c.id == task_feedback_table.c.task_id
                    )
                )
                .where(tasks_table.c.prompt_id == prompt_id)
            )
            
            result = await session.execute(stmt)
            row = result.fetchone()
            
            return {
                "num_interactions": row.num_interactions or 0,
                "average_feedback_score": float(row.average_feedback_score) if row.average_feedback_score is not None else None,
            }
        
        # Use provided session or create a new one
        if session:
            return await _calc(session)
        else:
            async with self._get_session_with_schema() as new_session:
                return await _calc(new_session)
