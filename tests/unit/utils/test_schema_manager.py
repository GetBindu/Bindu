"""Comprehensive tests for schema_manager utilities."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bindu.utils.schema_manager import (
    sanitize_did_for_schema,
    create_schema_if_not_exists,
    set_search_path,
    initialize_did_schema,
)


class TestSanitizeDIDForSchema:
    """Test DID sanitization for PostgreSQL schema names."""

    def test_basic_did_sanitization(self):
        """Test basic DID sanitization."""
        did = "did:bindu:alice:agent1:abc123"
        result = sanitize_did_for_schema(did)
        assert result == "did_bindu_alice_agent1_abc123"

    def test_uppercase_normalization(self):
        """Test that uppercase characters are normalized to lowercase."""
        did = "DID:BINDU:ALICE:AGENT1:ABC123"
        result = sanitize_did_for_schema(did)
        assert result == "did_bindu_alice_agent1_abc123"

    def test_special_characters_replaced(self):
        """Test that special characters are replaced with underscores."""
        did = "did:bindu:alice@example.com:agent-1"
        result = sanitize_did_for_schema(did)
        assert result == "did_bindu_alice_example_com_agent_1"

    def test_numeric_prefix_handling(self):
        """Test that numeric prefixes get 'schema_' prepended."""
        did = "123:numeric:start"
        result = sanitize_did_for_schema(did)
        assert result.startswith("schema_")
        assert "123_numeric_start" in result

    def test_long_did_truncation(self):
        """Test that long DIDs are truncated to 63 characters with hash."""
        # Create a DID longer than 63 characters
        long_did = "did:bindu:" + "a" * 100
        result = sanitize_did_for_schema(long_did)

        assert len(result) == 63
        # Should contain hash suffix
        assert "_" in result
        # Hash should be 8 characters
        parts = result.rsplit("_", 1)
        assert len(parts) == 2
        assert len(parts[1]) == 8

    def test_exactly_63_characters(self):
        """Test DID that is exactly 63 characters."""
        # Create a DID that results in exactly 63 characters
        did = "did:bindu:" + "a" * 52  # Total: 10 + 52 = 62 chars after replacement
        result = sanitize_did_for_schema(did)
        assert len(result) <= 63

    def test_empty_did(self):
        """Test empty DID string."""
        did = ""
        result = sanitize_did_for_schema(did)
        assert result == ""

    def test_only_special_characters(self):
        """Test DID with only special characters."""
        did = ":::---:::"
        result = sanitize_did_for_schema(did)
        assert result == "_________"

    def test_unicode_characters(self):
        """Test DID with unicode characters."""
        did = "did:bindu:用户:agent"
        result = sanitize_did_for_schema(did)
        # Unicode should be replaced with underscores
        assert "did_bindu_" in result


class TestCreateSchemaIfNotExists:
    """Test schema creation functionality."""

    @pytest.mark.asyncio
    async def test_create_new_schema(self):
        """Test creating a new schema that doesn't exist."""
        mock_conn = AsyncMock()

        # Mock schema check - schema doesn't exist
        mock_check_result = MagicMock()
        mock_check_result.first.return_value = None

        mock_conn.execute.side_effect = [mock_check_result, AsyncMock()]
        mock_conn.commit = AsyncMock()

        result = await create_schema_if_not_exists(mock_conn, "test_schema")

        assert result is True
        assert mock_conn.execute.call_count == 2
        mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_schema_already_exists(self):
        """Test when schema already exists."""
        mock_conn = AsyncMock()

        # Mock schema check - schema exists
        mock_check_result = MagicMock()
        mock_check_result.first.return_value = MagicMock()

        mock_conn.execute.return_value = mock_check_result

        result = await create_schema_if_not_exists(mock_conn, "existing_schema")

        assert result is False
        # Should only check, not create
        assert mock_conn.execute.call_count == 1
        mock_conn.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_schema_with_special_name(self):
        """Test creating schema with sanitized name."""
        mock_conn = AsyncMock()

        mock_check_result = MagicMock()
        mock_check_result.first.return_value = None

        mock_conn.execute.side_effect = [mock_check_result, AsyncMock()]
        mock_conn.commit = AsyncMock()

        schema_name = "did_bindu_alice_agent1"
        result = await create_schema_if_not_exists(mock_conn, schema_name)

        assert result is True
        # Verify CREATE SCHEMA was called with quoted name
        create_call = mock_conn.execute.call_args_list[1]
        sql_arg = create_call[0][0]
        sql_text = str(sql_arg)
        assert "CREATE SCHEMA" in sql_text and "did_bindu_alice_agent1" in sql_text


class TestSetSearchPath:
    """Test search_path configuration."""

    @pytest.mark.asyncio
    async def test_set_search_path_single_schema(self):
        """Test setting search_path to a single schema."""
        mock_conn = AsyncMock()

        await set_search_path(mock_conn, "test_schema")

        mock_conn.execute.assert_called_once()
        sql_arg = mock_conn.execute.call_args[0][0]
        sql_text = str(sql_arg)
        assert "test_schema" in sql_text
        assert "SET search_path" in sql_text

    @pytest.mark.asyncio
    async def test_set_search_path_with_public(self):
        """Test setting search_path including public schema."""
        mock_conn = AsyncMock()

        await set_search_path(mock_conn, "test_schema", include_public=True)

        mock_conn.execute.assert_called_once()
        sql_arg = mock_conn.execute.call_args[0][0]
        sql_text = str(sql_arg)
        assert "test_schema" in sql_text
        assert "public" in sql_text

    @pytest.mark.asyncio
    async def test_set_search_path_without_public(self):
        """Test setting search_path without public schema."""
        mock_conn = AsyncMock()

        await set_search_path(mock_conn, "test_schema", include_public=False)

        mock_conn.execute.assert_called_once()
        sql_arg = mock_conn.execute.call_args[0][0]
        sql_text = str(sql_arg)
        assert "test_schema" in sql_text
        # Should not include public when include_public=False
        assert "public" not in sql_text or sql_text.count("public") == 0


class TestInitializeDIDSchema:
    """Test complete DID schema initialization."""

    @pytest.mark.asyncio
    async def test_initialize_new_schema_with_tables(self):
        """Test initializing a new schema with table creation."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()

        # Mock schema creation
        mock_check_result = MagicMock()
        mock_check_result.first.return_value = None

        mock_conn.execute.side_effect = [mock_check_result, AsyncMock(), AsyncMock()]
        mock_conn.commit = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        # Mock engine.begin() context manager
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        mock_engine.begin.return_value.__aexit__.return_value = None

        schema_name = await initialize_did_schema(
            mock_engine, "test_schema", create_tables=True
        )

        assert schema_name == "test_schema"
        # Should be called twice: once for schema creation, once for table creation
        assert mock_engine.begin.call_count == 2
        mock_conn.run_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_existing_schema_with_tables(self):
        """Test initializing an existing schema with table creation."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()

        # Mock schema already exists
        mock_check_result = MagicMock()
        mock_check_result.first.return_value = MagicMock()

        mock_conn.execute.side_effect = [mock_check_result, AsyncMock()]
        mock_conn.run_sync = AsyncMock()

        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        mock_engine.begin.return_value.__aexit__.return_value = None

        schema_name = await initialize_did_schema(
            mock_engine, "existing_schema", create_tables=True
        )

        assert schema_name == "existing_schema"
        # Should still create tables even if schema exists
        mock_conn.run_sync.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_schema_without_tables(self):
        """Test initializing schema without creating tables."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()

        mock_check_result = MagicMock()
        mock_check_result.first.return_value = None

        mock_conn.execute.side_effect = [mock_check_result, AsyncMock()]
        mock_conn.commit = AsyncMock()

        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        mock_engine.begin.return_value.__aexit__.return_value = None

        schema_name = await initialize_did_schema(
            mock_engine, "test_schema", create_tables=False
        )

        assert schema_name == "test_schema"
        # Should only call begin once for schema creation
        assert mock_engine.begin.call_count == 1
        # Should not call run_sync for table creation
        mock_conn.run_sync.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_schema_full_workflow(self):
        """Test full workflow with DID sanitization and schema creation."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()

        # Sanitize DID
        did = "did:bindu:alice:agent1:abc123"
        schema_name = sanitize_did_for_schema(did)

        # Mock schema creation
        mock_check_result = MagicMock()
        mock_check_result.first.return_value = None

        mock_conn.execute.side_effect = [mock_check_result, AsyncMock(), AsyncMock()]
        mock_conn.commit = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        mock_engine.begin.return_value.__aexit__.return_value = None

        result = await initialize_did_schema(
            mock_engine, schema_name, create_tables=True
        )

        assert result == "did_bindu_alice_agent1_abc123"
        assert mock_engine.begin.call_count == 2


class TestIntegration:
    """Integration tests for schema management workflow."""

    def test_sanitize_and_validate_length(self):
        """Test that sanitized names are always valid PostgreSQL identifiers."""
        test_dids = [
            "did:bindu:alice",
            "did:bindu:" + "x" * 100,
            "123:numeric",
            "did:special:chars!@#$%",
            "DID:UPPERCASE:TEST",
        ]

        for did in test_dids:
            result = sanitize_did_for_schema(did)
            # Must be <= 63 characters
            assert len(result) <= 63
            # Must start with letter or underscore
            assert result[0].isalpha() or result[0] == "_"
            # Must contain only alphanumeric and underscores
            assert all(c.isalnum() or c == "_" for c in result)

    def test_hash_consistency(self):
        """Test that long DIDs produce consistent hashes."""
        long_did = "did:bindu:" + "a" * 100

        result1 = sanitize_did_for_schema(long_did)
        result2 = sanitize_did_for_schema(long_did)

        assert result1 == result2
        assert len(result1) == 63
