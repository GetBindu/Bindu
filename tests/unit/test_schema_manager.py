import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bindu.utils.schema_manager import (
    sanitize_did_for_schema,
    create_schema_if_not_exists,
    drop_schema_if_exists,
    set_search_path,
    list_schemas,
    get_tables_in_schema,
    initialize_did_schema,
)


def test_basic_sanitization():
    did = "did:bindu:alice:agent1:abc123"
    result = sanitize_did_for_schema(did)

    assert result == "did_bindu_alice_agent1_abc123"


def test_lowercasing():
    did = "DID:Bindu:ALICE"
    result = sanitize_did_for_schema(did)

    assert result == "did_bindu_alice"


def test_digit_prefix():
    did = "123:alice"
    result = sanitize_did_for_schema(did)

    assert result.startswith("schema_")
    assert result == "schema_123_alice"


def test_truncation_and_hashing():
    long_did = "did:bindu:" + "a" * 100
    result = sanitize_did_for_schema(long_did)

    # PostgreSQL max length
    assert len(result) <= 63

    # Should contain hash suffix
    assert "_" in result
    assert len(result.split("_")[-1]) == 8


def test_deterministic_hashing():
    long_did = "did:bindu:" + "x" * 100

    result1 = sanitize_did_for_schema(long_did)
    result2 = sanitize_did_for_schema(long_did)

    assert result1 == result2


@pytest.mark.asyncio
async def test_create_schema_if_not_exists_already_exists():
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = ("schema_name",)
    mock_conn.execute.return_value = mock_result

    result = await create_schema_if_not_exists(mock_conn, "test_schema")
    assert result is False
    mock_conn.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_schema_if_not_exists_creates():
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_conn.execute.return_value = mock_result

    result = await create_schema_if_not_exists(mock_conn, "test_schema")
    assert result is True
    mock_conn.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_drop_schema_if_exists_not_exist():
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_conn.execute.return_value = mock_result

    result = await drop_schema_if_exists(mock_conn, "test_schema")
    assert result is False


@pytest.mark.asyncio
async def test_drop_schema_if_exists_drops():
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = ("schema_name",)
    mock_conn.execute.return_value = mock_result

    result = await drop_schema_if_exists(mock_conn, "test_schema")
    assert result is True
    mock_conn.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_search_path():
    mock_conn = AsyncMock()
    await set_search_path(mock_conn, "test_schema")
    mock_conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_search_path_public():
    mock_conn = AsyncMock()
    await set_search_path(mock_conn, "test_schema", True)
    mock_conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_schemas():
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("schema1",), ("schema2",)]
    mock_conn.execute.return_value = mock_result

    result = await list_schemas(mock_conn)
    assert result == ["schema1", "schema2"]


@pytest.mark.asyncio
async def test_get_tables_in_schema():
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("table1",), ("table2",)]
    mock_conn.execute.return_value = mock_result

    result = await get_tables_in_schema(mock_conn, "schema1")
    assert result == ["table1", "table2"]


@pytest.mark.asyncio
@patch("bindu.utils.schema_manager.create_schema_if_not_exists")
@patch("bindu.utils.schema_manager.set_search_path")
async def test_initialize_did_schema(mock_set, mock_create):
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_engine.begin.return_value = mock_context
    mock_create.return_value = True

    result = await initialize_did_schema(mock_engine, "test_schema", create_tables=True)
    assert result == "test_schema"
    mock_conn.run_sync.assert_awaited_once()
