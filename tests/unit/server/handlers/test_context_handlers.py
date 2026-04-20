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
        # caller_did defaults to None → storage receives owner_did=None,
        # which means "no owner filter" (dev-mode behavior).
        mock_storage.list_contexts.assert_called_once_with(10, owner_did=None)

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
        """Test clearing context successfully (unauthenticated caller on an
        unowned context — the dev-mode default where caller_did and owner
        both equal None)."""
        mock_storage = AsyncMock()
        mock_storage.clear_context.return_value = None
        # Unauthenticated clear requires caller_did == owner == None
        mock_storage.get_context_owner.return_value = None

        handler = ContextHandlers(storage=mock_storage)
        request = {"jsonrpc": "2.0", "id": "3", "params": {"contextId": "ctx123"}}

        response = await handler.clear_context(request)

        assert response["jsonrpc"] == "2.0"
        assert "cleared successfully" in response["result"]["message"]
        mock_storage.clear_context.assert_called_once_with("ctx123")

    @pytest.mark.asyncio
    async def test_clear_context_not_found(self):
        """Test clearing non-existent context — storage raises ValueError
        after the ownership precheck passes (matched NULL-owner for an
        unauthenticated caller)."""
        mock_storage = AsyncMock()
        # Pass the ownership precheck: caller_did=None == owner=None
        mock_storage.get_context_owner.return_value = None
        mock_storage.clear_context.side_effect = ValueError("Context not found")

        mock_error_creator = Mock(return_value={"error": "not found"})
        handler = ContextHandlers(
            storage=mock_storage, error_response_creator=mock_error_creator
        )
        request = {"jsonrpc": "2.0", "id": "4", "params": {"contextId": "invalid"}}

        response = await handler.clear_context(request)

        assert "error" in response
        mock_error_creator.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_context_cross_tenant_blocked(self):
        """Test that a caller cannot clear a context owned by another DID.
        The error is ContextNotFound, not a distinct 'forbidden' — so
        cross-tenant UUID probing cannot distinguish existence."""
        mock_storage = AsyncMock()
        # Context exists with owner=alice
        mock_storage.get_context_owner.return_value = "did:bindu:alice"

        mock_error_creator = Mock(return_value={"error": "not found"})
        handler = ContextHandlers(
            storage=mock_storage, error_response_creator=mock_error_creator
        )
        request = {"jsonrpc": "2.0", "id": "5", "params": {"contextId": "ctx123"}}

        # Bob tries to clear Alice's context
        response = await handler.clear_context(request, caller_did="did:bindu:bob")

        assert "error" in response
        mock_error_creator.assert_called_once()
        # storage.clear_context must NOT have been called
        mock_storage.clear_context.assert_not_called()
