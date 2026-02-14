"""Unit tests for A2A protocol endpoint."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import (
    InternalError,
    JSONParseError,
    MethodNotFoundError,
)
from bindu.server.applications import BinduApplication
from bindu.server.endpoints.a2a_protocol import agent_run_endpoint


@pytest.fixture
def mock_app():
    """Create a mock BinduApplication."""
    app = MagicMock(spec=BinduApplication)
    app.task_manager = MagicMock()
    # Mock the handler method on task_manager
    app.task_manager.mock_handler = AsyncMock(return_value={"result": "success"})
    return app


@pytest.fixture
def mock_settings():
    """Mock app settings."""
    with patch("bindu.server.endpoints.a2a_protocol.app_settings") as mock:
        mock.agent.method_handlers = {
            "tasks/list": "mock_handler",
            "message/send": "mock_handler",
        }
        yield mock


@pytest.mark.asyncio
async def test_valid_request(mock_app, mock_settings):
    """Test successful processing of a valid A2A request."""
    # Setup request with valid JSON body
    body = {
        "jsonrpc": "2.0",
        "method": "tasks/list",
        "params": {},
        "id": str(uuid.uuid4()),
    }
    
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=json.dumps(body).encode())
    mock_request.state = MagicMock()
    # Ensure payment attributes are not present to test plain request
    del mock_request.state.payment_payload
    del mock_request.state.payment_requirements
    del mock_request.state.verify_response

    # Call endpoint
    response = await agent_run_endpoint(mock_app, mock_request)

    # Verify task manager handler was called
    mock_app.task_manager.mock_handler.assert_called_once()
    
    # Verify response
    assert isinstance(response, Response)
    assert response.status_code == 200
    content = json.loads(response.body)
    assert content["result"] == "success"


@pytest.mark.asyncio
async def test_invalid_json(mock_app):
    """Test handling of invalid JSON body."""
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b"invalid json")

    response = await agent_run_endpoint(mock_app, mock_request)

    assert response.status_code == 400  # Invalid JSON results in 400 Bad Request
    # Note: Starlette/FastAPI/Pydantic validation layer returns 400 for structural errors
    # before reaching JSON-RPC handler logic that would return 200 with error object.


@pytest.mark.asyncio
async def test_unsupported_method(mock_app, mock_settings):
    """Test handling of unsupported method."""
    body = {
        "jsonrpc": "2.0",
        "method": "unknown/method",
        "id": str(uuid.uuid4()),
    }
    
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=json.dumps(body).encode())

    response = await agent_run_endpoint(mock_app, mock_request)

    assert response.status_code == 400
    # Validation fails for unknown method tag in discriminated union


@pytest.mark.asyncio
async def test_internal_error(mock_app, mock_settings):
    """Test handling of internal errors."""
    body = {
        "jsonrpc": "2.0",
        "method": "tasks/list",
        "params": {},
        "id": str(uuid.uuid4()),
    }
    
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=json.dumps(body).encode())
    
    # Simulate handler raising exception
    mock_app.task_manager.mock_handler.side_effect = Exception("Crash")

    response = await agent_run_endpoint(mock_app, mock_request)

    assert response.status_code == 500
    content = json.loads(response.body)
    assert "error" in content
    assert content["error"]["code"] == -32603  # Internal error


@pytest.mark.asyncio
async def test_payment_context_injection(mock_app):
    """Test injection of payment context into message metadata."""
    # Mock settings specifically for this test to ensure handler is found
    with patch("bindu.server.endpoints.a2a_protocol.app_settings") as mock_settings:
        mock_settings.agent.method_handlers = {"message/send": "mock_handler"}
        
        body = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "configuration": {
                    "acceptedOutputModes": ["text"]
                },
                "message": {
                    "messageId": "123e4567-e89b-12d3-a456-426614174000",
                    "contextId": "123e4567-e89b-12d3-a456-426614174001",
                    "taskId": "123e4567-e89b-12d3-a456-426614174002",
                    "kind": "message",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "hello"}]
                }
            },
            "id": str(uuid.uuid4()),
        }
        
        mock_request = MagicMock(spec=Request)
        mock_request.body = AsyncMock(return_value=json.dumps(body).encode())
        
        # Setup payment context in request state
        mock_request.state.payment_payload = {"amount": 100}
        mock_request.state.payment_requirements = {"token": "USDC"}
        mock_request.state.verify_response = {"status": "verified"}

        # Call endpoint
        await agent_run_endpoint(mock_app, mock_request)

        # Verify handler called with modified request
        call_args = mock_app.task_manager.mock_handler.call_args[0][0]
        metadata = call_args["params"]["message"]["metadata"]
        
        assert "_payment_context" in metadata
        context = metadata["_payment_context"]
        assert context["payment_payload"] == {"amount": 100}
        assert context["payment_requirements"] == {"token": "USDC"}
        assert context["verify_response"] == {"status": "verified"}
