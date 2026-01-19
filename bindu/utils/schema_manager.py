"""Schema management utilities for DID-based multi-tenancy.

This module provides utilities for creating and managing PostgreSQL schemas
for each DID (Decentralized Identifier), enabling true multi-tenancy isolation.

Each DID gets its own schema containing all tables (tasks, contexts, etc.),
providing complete logical separation between different agents.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger("bindu.utils.schema_manager")


def sanitize_did_for_schema(did: str) -> str:
    """Sanitize a DID string to be used as a PostgreSQL schema name.

    PostgreSQL schema names must:
    - Start with a letter or underscore
    - Contain only letters, digits, and underscores
    - Be <= 63 characters
    - Not be a reserved keyword

    For long DIDs (>63 chars), uses a hash suffix to maintain uniqueness
    while keeping the schema name readable and within PostgreSQL limits.

    Args:
        did: DID string (e.g., "did:bindu:alice:agent1:abc123")

    Returns:
        Sanitized schema name (e.g., "did_bindu_alice_agent1_abc123")

    Examples:
        >>> sanitize_did_for_schema("did:bindu:alice:agent1:abc123")
        'did_bindu_alice_agent1_abc123'
        >>> sanitize_did_for_schema("did:bindu:very_long_email_address:agent:uuid")
        'did_bindu_very_long_email_address_agent_uuid_a1b2c3d4'
    """
    import hashlib

    # Replace colons and other special characters with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", did.lower())

    # Ensure it starts with a letter or underscore
    if sanitized and sanitized[0].isdigit():
        sanitized = f"schema_{sanitized}"

    # Truncate if too long (PostgreSQL limit is 63 chars)
    # Use hash suffix to maintain uniqueness
    if len(sanitized) > 63:
        # Generate 8-character hash from the full sanitized string
        hash_suffix = hashlib.sha256(sanitized.encode()).hexdigest()[:8]
        # Keep first 54 chars + underscore + 8 char hash = 63 chars total
        sanitized = f"{sanitized[:54]}_{hash_suffix}"

    return sanitized


async def create_schema_if_not_exists(
    connection: AsyncConnection, schema_name: str
) -> bool:
    """Create a PostgreSQL schema if it doesn't already exist.

    Args:
        connection: SQLAlchemy async connection
        schema_name: Name of the schema to create

    Returns:
        True if schema was created, False if it already existed

    Raises:
        Exception: If schema creation fails
    """
    # Check if schema exists
    result = await connection.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = :schema_name"
        ),
        {"schema_name": schema_name},
    )
    exists = result.first() is not None

    if exists:
        logger.debug(f"Schema '{schema_name}' already exists")
        return False

    # Create schema
    # Note: We can't use parameterized queries for DDL statements
    # The schema name is sanitized, so this is safe
    await connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    await connection.commit()

    logger.info(f"Created schema '{schema_name}'")
    return True


async def drop_schema_if_exists(
    connection: AsyncConnection, schema_name: str, cascade: bool = False
) -> bool:
    """Drop a PostgreSQL schema if it exists.

    Args:
        connection: SQLAlchemy async connection
        schema_name: Name of the schema to drop
        cascade: If True, drop all objects in the schema as well

    Returns:
        True if schema was dropped, False if it didn't exist

    Raises:
        Exception: If schema drop fails

    Warning:
        This is a destructive operation. Use with caution!
    """
    # Check if schema exists
    result = await connection.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = :schema_name"
        ),
        {"schema_name": schema_name},
    )
    exists = result.first() is not None

    if not exists:
        logger.debug(f"Schema '{schema_name}' does not exist")
        return False

    # Drop schema
    cascade_clause = "CASCADE" if cascade else "RESTRICT"
    await connection.execute(text(f'DROP SCHEMA "{schema_name}" {cascade_clause}'))
    await connection.commit()

    logger.warning(f"Dropped schema '{schema_name}' ({cascade_clause})")
    return True


async def set_search_path(
    connection: AsyncConnection, schema_name: str, include_public: bool = False
) -> None:
    """Set the search_path for the current connection to use a specific schema.

    This makes all queries use the specified schema by default without
    needing to qualify table names.

    Args:
        connection: SQLAlchemy async connection
        schema_name: Schema to set as the search path
        include_public: If True, also include 'public' schema in search path

    Example:
        After setting search_path to 'did_bindu_alice_agent1':
        - SELECT * FROM tasks  -> searches in did_bindu_alice_agent1.tasks
        - No need to write: SELECT * FROM did_bindu_alice_agent1.tasks
    """
    if include_public:
        search_path = f'"{schema_name}", public'
    else:
        search_path = f'"{schema_name}"'

    await connection.execute(text(f"SET search_path TO {search_path}"))
    logger.debug(f"Set search_path to: {search_path}")


async def list_schemas(connection: AsyncConnection) -> list[str]:
    """List all non-system schemas in the database.

    Args:
        connection: SQLAlchemy async connection

    Returns:
        List of schema names (excluding pg_* and information_schema)
    """
    result = await connection.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name NOT LIKE 'pg_%' "
            "AND schema_name != 'information_schema' "
            "ORDER BY schema_name"
        )
    )
    return [row[0] for row in result.fetchall()]


async def get_tables_in_schema(
    connection: AsyncConnection, schema_name: str
) -> list[str]:
    """Get all table names in a specific schema.

    Args:
        connection: SQLAlchemy async connection
        schema_name: Schema to query

    Returns:
        List of table names in the schema
    """
    result = await connection.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = :schema_name "
            "AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        ),
        {"schema_name": schema_name},
    )
    return [row[0] for row in result.fetchall()]


async def initialize_did_schema(
    engine: AsyncEngine, schema_name: str, create_tables: bool = True
) -> str:
    """Initialize a complete schema for a DID with all necessary tables.

    This is the main entry point for setting up a new DID's database schema.

    Args:
        engine: SQLAlchemy async engine
        schema_name: Sanitized schema name (use sanitize_did_for_schema() to generate)
        create_tables: If True, create all tables in the schema

    Returns:
        The schema name that was created/initialized

    Example:
        >>> schema_name = sanitize_did_for_schema("did:bindu:alice:agent1:abc123")
        >>> await initialize_did_schema(engine, schema_name)
        >>> # Creates schema 'did_bindu_alice_agent1_abc123' with all tables
    """
    # Create the schema first (separate transaction)
    async with engine.begin() as conn:
        created = await create_schema_if_not_exists(conn, schema_name)

    # Create tables in a separate transaction to avoid conflicts
    if create_tables:
        async with engine.begin() as conn:
            # Set search path to the new schema
            await set_search_path(conn, schema_name)

            # Create all tables in this schema
            from bindu.server.storage.schema import metadata

            # Create tables using run_sync
            def create_tables_sync(sync_conn):
                metadata.create_all(sync_conn, checkfirst=True)

            await conn.run_sync(create_tables_sync)

        if created:
            logger.info(f"Initialized schema '{schema_name}' with all tables")
        else:
            logger.info(
                f"Schema '{schema_name}' already exists, ensured tables are created"
            )
    elif created:
        logger.info(f"Created empty schema '{schema_name}'")
    return schema_name
