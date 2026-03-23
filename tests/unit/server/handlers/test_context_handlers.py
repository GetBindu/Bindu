"""Minimal tests for context handlers."""

from unittest.mock import AsyncMock, Mock
import pytest

from bindu.server.handlers.context_handlers import ContextHandlers


class TestContextHandlers:
    """Test context handler functionality."""

    @pytest.mark.asyncio
    async def test_list_contexts_success(self):
        """Test listing contexts successfully."""
        mock_storage = AsyncMock()
        mock_storage.list_contexts.return_value = [
            {"id": "ctx1", "name": "Context 1"},
            {"id": "ctx2", "name": "Context 2"},
        ]

        handler = ContextHandlers(storage=mock_storage)
        request = {"jsonrpc": "2.0", "id": "1", "params": {"length": 10}}

        response = await handler.list_contexts(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert len(response["result"]) == 2
        mock_storage.list_contexts.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_list_contexts_empty(self):
        """Test listing contexts when none exist."""
        mock_storage = AsyncMock()
        mock_storage.list_contexts.return_value = None

        handler = ContextHandlers(storage=mock_storage)
        request = {"jsonrpc": "2.0", "id": "2", "params": {}}

        response = await handler.list_contexts(request)

        assert response["result"] == []

    @pytest.mark.asyncio
    async def test_list_contexts_no_params(self):
        """Test listing contexts with no params."""
        mock_storage = AsyncMock()
        mock_storage.list_contexts.return_value = None

        handler = ContextHandlers(storage=mock_storage)
        request = {"jsonrpc": "2.0", "id": "2"}

        response = await handler.list_contexts(request)

        assert response["result"] == []

    @pytest.mark.asyncio
    async def test_clear_context_success(self):
        """Test clearing context successfully."""
        mock_storage = AsyncMock()
        mock_storage.clear_context.return_value = None

        handler = ContextHandlers(storage=mock_storage)
        request = {"jsonrpc": "2.0", "id": "3", "params": {"contextId": "ctx123"}}

        response = await handler.clear_context(request)

        assert response["jsonrpc"] == "2.0"
        assert "cleared successfully" in response["result"]["message"]
        mock_storage.clear_context.assert_called_once_with("ctx123")

    @pytest.mark.asyncio
    async def test_clear_context_not_found(self):
        """Test clearing non-existent context."""
        mock_storage = AsyncMock()
        mock_storage.clear_context.side_effect = ValueError("Context not found")

        mock_error_creator = Mock(return_value={"error": "not found"})
        handler = ContextHandlers(
            storage=mock_storage, error_response_creator=mock_error_creator
        )
        request = {"jsonrpc": "2.0", "id": "4", "params": {"contextId": "invalid"}}

        response = await handler.clear_context(request)

        assert "error" in response
        mock_error_creator.assert_called_once()
