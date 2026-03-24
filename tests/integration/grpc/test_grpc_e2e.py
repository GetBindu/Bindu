"""End-to-end tests for gRPC language-agnostic agent support.

These tests verify the complete flow:
    1. Start gRPC server on :3774
    2. Start a mock AgentHandler (simulates a TypeScript/Kotlin SDK)
    3. Register agent via BinduService.RegisterAgent
    4. Send A2A message via HTTP to :3773
    5. Verify the message flows through: HTTP → TaskManager → Scheduler →
       Worker → GrpcAgentClient → AgentHandler → response
    6. Verify task completes with correct response and DID signature

These tests require real network ports and are marked as e2e/slow.
Run with: uv run pytest tests/integration/grpc/ -v -m e2e
"""

from __future__ import annotations

import json
import time
from concurrent import futures
from typing import Any

import grpc
import httpx
import pytest

from bindu.grpc.generated import agent_handler_pb2, agent_handler_pb2_grpc
from bindu.grpc.registry import AgentRegistry
from bindu.grpc.server import start_grpc_server


# ---------------------------------------------------------------------------
# Mock AgentHandler — simulates what a TypeScript/Kotlin SDK would run
# ---------------------------------------------------------------------------


class MockAgentHandler(agent_handler_pb2_grpc.AgentHandlerServicer):
    """A mock AgentHandler that echoes messages back.

    This simulates what the TypeScript or Kotlin SDK's gRPC server does:
    receives HandleMessages calls from the Bindu core and returns responses.
    """

    def __init__(self) -> None:
        self.calls: list[agent_handler_pb2.HandleRequest] = []

    def HandleMessages(
        self,
        request: agent_handler_pb2.HandleRequest,
        context: grpc.ServicerContext,
    ) -> agent_handler_pb2.HandleResponse:
        """Echo the last message content back."""
        self.calls.append(request)
        last_message = request.messages[-1] if request.messages else None
        content = f"Echo: {last_message.content}" if last_message else "No messages"
        return agent_handler_pb2.HandleResponse(
            content=content,
            state="",
            prompt="",
            is_final=True,
        )

    def HandleMessagesStream(
        self,
        request: agent_handler_pb2.HandleRequest,
        context: grpc.ServicerContext,
    ) -> Any:
        """Stream back chunks — simulates streaming handler."""
        self.calls.append(request)
        last_message = request.messages[-1] if request.messages else None
        content = last_message.content if last_message else ""

        # Yield two chunks: thinking + final
        yield agent_handler_pb2.HandleResponse(
            content=f"Processing: {content}",
            state="",
            is_final=False,
        )
        yield agent_handler_pb2.HandleResponse(
            content=f"Echo: {content}",
            state="",
            is_final=True,
        )

    def GetCapabilities(
        self,
        request: agent_handler_pb2.GetCapabilitiesRequest,
        context: grpc.ServicerContext,
    ) -> agent_handler_pb2.GetCapabilitiesResponse:
        """Return mock capabilities."""
        return agent_handler_pb2.GetCapabilitiesResponse(
            name="mock-agent",
            version="1.0.0",
            supports_streaming=True,
        )

    def HealthCheck(
        self,
        request: agent_handler_pb2.HealthCheckRequest,
        context: grpc.ServicerContext,
    ) -> agent_handler_pb2.HealthCheckResponse:
        """Always healthy."""
        return agent_handler_pb2.HealthCheckResponse(
            healthy=True,
            message="OK",
        )


def _start_mock_agent_handler(port: int) -> tuple[grpc.Server, MockAgentHandler]:
    """Start a mock AgentHandler gRPC server on the given port.

    Args:
        port: Port to bind the mock server to.

    Returns:
        Tuple of (server, handler) — handler tracks calls for assertions.
    """
    handler = MockAgentHandler()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    agent_handler_pb2_grpc.add_AgentHandlerServicer_to_server(handler, server)
    server.add_insecure_port(f"localhost:{port}")
    server.start()
    return server, handler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GRPC_PORT = 13774  # Non-standard port to avoid conflicts
CALLBACK_PORT = 13999  # Mock agent handler port
HTTP_PORT = 13773  # A2A HTTP server port


@pytest.fixture(scope="module")
def grpc_server():
    """Start the Bindu core gRPC server for the test session."""
    registry = AgentRegistry()
    server = start_grpc_server(registry=registry, port=GRPC_PORT, host="localhost")
    yield server, registry
    server.stop(grace=1)


@pytest.fixture(scope="module")
def mock_agent():
    """Start a mock AgentHandler simulating a TypeScript/Kotlin SDK."""
    server, handler = _start_mock_agent_handler(CALLBACK_PORT)
    yield handler
    server.stop(grace=1)


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.slow
class TestGrpcE2ERegistration:
    """Test the full registration flow: SDK → gRPC → Core → bindufy."""

    def test_heartbeat_unregistered(self, grpc_server: Any) -> None:
        """Test heartbeat for an unregistered agent returns acknowledged=False."""
        channel = grpc.insecure_channel(f"localhost:{GRPC_PORT}")
        stub = agent_handler_pb2_grpc.BinduServiceStub(channel)

        response = stub.Heartbeat(
            agent_handler_pb2.HeartbeatRequest(
                agent_id="nonexistent",
                timestamp=int(time.time() * 1000),
            )
        )

        assert response.acknowledged is False
        assert response.server_timestamp > 0
        channel.close()

    def test_register_agent(
        self, grpc_server: Any, mock_agent: MockAgentHandler
    ) -> None:
        """Test full RegisterAgent flow — DID, manifest, HTTP server."""
        channel = grpc.insecure_channel(f"localhost:{GRPC_PORT}")
        stub = agent_handler_pb2_grpc.BinduServiceStub(channel)

        config = {
            "author": "e2e-test@bindu.com",
            "name": "e2e-test-agent",
            "description": "E2E test agent",
            "deployment": {
                "url": f"http://localhost:{HTTP_PORT}",
                "expose": True,
            },
        }

        response = stub.RegisterAgent(
            agent_handler_pb2.RegisterAgentRequest(
                config_json=json.dumps(config),
                skills=[],
                grpc_callback_address=f"localhost:{CALLBACK_PORT}",
            )
        )

        assert response.success is True
        assert response.agent_id != ""
        assert response.did.startswith("did:bindu:")
        assert response.agent_url == f"http://localhost:{HTTP_PORT}"

        # Wait for uvicorn to start
        time.sleep(3)

        channel.close()

    def test_heartbeat_registered(self, grpc_server: Any) -> None:
        """Test heartbeat for a registered agent returns acknowledged=True."""
        _server, registry = grpc_server
        agents = registry.list_agents()

        # Should have at least one agent from the register test
        if not agents:
            pytest.skip("No agents registered — run test_register_agent first")

        agent_id = agents[0].agent_id

        channel = grpc.insecure_channel(f"localhost:{GRPC_PORT}")
        stub = agent_handler_pb2_grpc.BinduServiceStub(channel)

        response = stub.Heartbeat(
            agent_handler_pb2.HeartbeatRequest(
                agent_id=agent_id,
                timestamp=int(time.time() * 1000),
            )
        )

        assert response.acknowledged is True
        channel.close()


@pytest.mark.e2e
@pytest.mark.slow
class TestGrpcE2EMessageFlow:
    """Test the full message flow: HTTP → Core → gRPC → SDK → response."""

    def test_agent_card_available(self, grpc_server: Any, mock_agent: Any) -> None:
        """Test that the A2A agent card is served after registration."""
        # Give the HTTP server time to fully start
        time.sleep(2)

        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"http://localhost:{HTTP_PORT}/.well-known/agent.json")

        assert resp.status_code == 200
        card = resp.json()
        assert card["name"] == "e2e-test-agent"
        assert "id" in card
        # DID is in capabilities.extensions[0].uri
        extensions = card.get("capabilities", {}).get("extensions", [])
        assert len(extensions) > 0
        assert extensions[0]["uri"].startswith("did:bindu:")

    def test_send_message_and_get_response(
        self, grpc_server: Any, mock_agent: MockAgentHandler
    ) -> None:
        """Test full round-trip: send A2A message → handler executes → task completes.

        This is the critical E2E test. It proves:
        1. A2A HTTP endpoint receives the message
        2. TaskManager schedules the task
        3. Worker calls manifest.run() which is GrpcAgentClient
        4. GrpcAgentClient calls HandleMessages on the mock agent
        5. Mock agent returns "Echo: Hello world!"
        6. Worker processes the response, creates artifacts
        7. Task completes with DID-signed artifact
        """
        task_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        context_id = "11111111-2222-3333-4444-555555555555"
        message_id = "66666666-7777-8888-9999-000000000000"

        a2a_request = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Hello world!"}],
                    "messageId": message_id,
                    "contextId": context_id,
                    "taskId": task_id,
                    "kind": "message",
                },
                "configuration": {
                    "acceptedOutputModes": ["text/plain"],
                    "blocking": True,
                },
            },
            "id": "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
        }

        # Send A2A message
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"http://localhost:{HTTP_PORT}",
                json=a2a_request,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 200
        result = resp.json()
        assert "result" in result

        # Wait for async task processing
        time.sleep(3)

        # Get the completed task
        get_task_request = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"taskId": task_id},
            "id": "99999999-8888-7777-6666-555555555555",
        }

        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                f"http://localhost:{HTTP_PORT}",
                json=get_task_request,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == 200
        task_result = resp.json()

        # Verify task completed
        task = task_result["result"]
        assert task["status"]["state"] == "completed"

        # Verify agent response in history
        agent_messages = [m for m in task["history"] if m["role"] == "agent"]
        assert len(agent_messages) >= 1

        agent_response = agent_messages[0]
        response_text = agent_response["parts"][0]["text"]
        assert response_text == "Echo: Hello world!"

        # Verify artifacts exist with DID signature
        assert len(task["artifacts"]) >= 1
        artifact = task["artifacts"][0]
        assert artifact["parts"][0]["text"] == "Echo: Hello world!"

        # Verify DID signature is present
        metadata = artifact["parts"][0].get("metadata", {})
        assert "did.message.signature" in metadata

        # Verify the mock handler was called
        assert len(mock_agent.calls) >= 1
        last_call = mock_agent.calls[-1]
        assert any(m.content == "Hello world!" for m in last_call.messages)

    def test_health_endpoint(self, grpc_server: Any, mock_agent: Any) -> None:
        """Test the /health endpoint works on the registered agent's server."""
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"http://localhost:{HTTP_PORT}/health")

        assert resp.status_code == 200
