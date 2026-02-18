"""Unit tests for the Collab Pipeline example.

Tests cover:
- A2A JSON-RPC request building
- Task artifact text extraction
- Orchestrator pipeline flow (mocked HTTP)
- Error handling (agent down, empty input, task failure)
"""

import asyncio
import uuid

import pytest

# ---------------------------------------------------------------------------
# Import orchestrator helpers
# ---------------------------------------------------------------------------
import sys
import os

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "examples", "collab_pipeline"
    ),
)

from collab_orchestrator import (
    build_message_send_request,
    build_task_get_request,
    extract_text_from_artifacts,
    send_message,
)


# ===================================================================
# Tests for build_message_send_request
# ===================================================================
class TestBuildMessageSendRequest:
    """Tests for the A2A message/send request builder."""

    def test_returns_valid_jsonrpc_structure(self):
        req = build_message_send_request("Hello, agent!")
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "message/send"
        assert "id" in req
        assert "params" in req
        assert "message" in req["params"]

    def test_message_contains_text_part(self):
        req = build_message_send_request("Test text")
        parts = req["params"]["message"]["parts"]
        assert len(parts) == 1
        assert parts[0]["kind"] == "text"
        assert parts[0]["text"] == "Test text"

    def test_message_role_is_user(self):
        req = build_message_send_request("Hello")
        assert req["params"]["message"]["role"] == "user"

    def test_auto_generates_context_id(self):
        req = build_message_send_request("Hello")
        context_id = req["params"]["message"]["context_id"]
        assert context_id is not None
        # Should be valid UUID
        uuid.UUID(context_id)

    def test_uses_provided_context_id(self):
        custom_ctx = "my-context-123"
        req = build_message_send_request("Hello", context_id=custom_ctx)
        assert req["params"]["message"]["context_id"] == custom_ctx

    def test_each_request_has_unique_id(self):
        req1 = build_message_send_request("a")
        req2 = build_message_send_request("b")
        assert req1["id"] != req2["id"]


# ===================================================================
# Tests for build_task_get_request
# ===================================================================
class TestBuildTaskGetRequest:
    """Tests for the A2A tasks/get request builder."""

    def test_returns_valid_jsonrpc_structure(self):
        req = build_task_get_request("task-abc")
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "tasks/get"
        assert req["params"]["task_id"] == "task-abc"

    def test_each_request_has_unique_id(self):
        req1 = build_task_get_request("task-1")
        req2 = build_task_get_request("task-2")
        assert req1["id"] != req2["id"]


# ===================================================================
# Tests for extract_text_from_artifacts
# ===================================================================
class TestExtractTextFromArtifacts:
    """Tests for extracting text content from completed task artifacts."""

    def test_extracts_single_text_artifact(self):
        task = {
            "artifacts": [
                {
                    "parts": [{"kind": "text", "text": "Summary here"}]
                }
            ]
        }
        assert extract_text_from_artifacts(task) == "Summary here"

    def test_extracts_multiple_text_parts(self):
        task = {
            "artifacts": [
                {
                    "parts": [
                        {"kind": "text", "text": "Part 1"},
                        {"kind": "text", "text": "Part 2"},
                    ]
                }
            ]
        }
        result = extract_text_from_artifacts(task)
        assert "Part 1" in result
        assert "Part 2" in result

    def test_returns_empty_for_no_artifacts(self):
        assert extract_text_from_artifacts({}) == ""
        assert extract_text_from_artifacts({"artifacts": []}) == ""

    def test_ignores_non_text_parts(self):
        task = {
            "artifacts": [
                {
                    "parts": [
                        {"kind": "image", "data": "base64..."},
                        {"kind": "text", "text": "Text content"},
                    ]
                }
            ]
        }
        result = extract_text_from_artifacts(task)
        assert result == "Text content"

    def test_handles_multiple_artifacts(self):
        task = {
            "artifacts": [
                {"parts": [{"kind": "text", "text": "First"}]},
                {"parts": [{"kind": "text", "text": "Second"}]},
            ]
        }
        result = extract_text_from_artifacts(task)
        assert "First" in result
        assert "Second" in result


# ===================================================================
# Tests for send_message (mocked HTTP)
# ===================================================================
class MockResponse:
    """Mock httpx response for testing."""

    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockClient:
    """Mock httpx.AsyncClient that returns predefined responses."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.call_count = 0

    async def post(self, url, json=None, timeout=None):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        raise RuntimeError("No more mock responses available")


class TestSendMessage:
    """Tests for the send_message function using mocked HTTP."""

    def test_immediate_completion(self):
        """Task completes immediately (no polling needed)."""
        responses = [
            MockResponse({
                "result": {
                    "id": "task-1",
                    "status": {"state": "completed"},
                    "artifacts": [
                        {"parts": [{"kind": "text", "text": "Result text"}]}
                    ],
                }
            })
        ]
        client = MockClient(responses)
        result = asyncio.get_event_loop().run_until_complete(
            send_message(client, "http://localhost:3773", "Test input")
        )
        assert result == "Result text"

    def test_polls_until_completion(self):
        """Task requires polling before completing."""
        responses = [
            # Initial message/send → submitted
            MockResponse({
                "result": {
                    "id": "task-2",
                    "status": {"state": "submitted"},
                    "artifacts": [],
                }
            }),
            # First poll → working
            MockResponse({
                "result": {
                    "id": "task-2",
                    "status": {"state": "working"},
                    "artifacts": [],
                }
            }),
            # Second poll → completed
            MockResponse({
                "result": {
                    "id": "task-2",
                    "status": {"state": "completed"},
                    "artifacts": [
                        {"parts": [{"kind": "text", "text": "Done!"}]}
                    ],
                }
            }),
        ]
        client = MockClient(responses)

        # Patch POLL_INTERVAL to speed up test
        import collab_orchestrator
        original_interval = collab_orchestrator.POLL_INTERVAL
        collab_orchestrator.POLL_INTERVAL = 0.01

        try:
            result = asyncio.get_event_loop().run_until_complete(
                send_message(client, "http://localhost:3773", "Test")
            )
            assert result == "Done!"
            assert client.call_count == 3  # 1 send + 2 polls
        finally:
            collab_orchestrator.POLL_INTERVAL = original_interval

    def test_raises_on_task_failure(self):
        """Should raise RuntimeError when task fails."""
        responses = [
            MockResponse({
                "result": {
                    "id": "task-fail",
                    "status": {"state": "failed"},
                    "artifacts": [],
                }
            })
        ]
        client = MockClient(responses)
        with pytest.raises(RuntimeError, match="failed"):
            asyncio.get_event_loop().run_until_complete(
                send_message(client, "http://localhost:3773", "Test")
            )

    def test_raises_on_a2a_error_response(self):
        """Should raise RuntimeError when A2A returns error."""
        responses = [
            MockResponse({
                "error": {"code": -32600, "message": "Invalid request"}
            })
        ]
        client = MockClient(responses)
        with pytest.raises(RuntimeError, match="A2A error"):
            asyncio.get_event_loop().run_until_complete(
                send_message(client, "http://localhost:3773", "Test")
            )

    def test_fallback_to_history_messages(self):
        """Should fall back to history when no artifacts are present."""
        responses = [
            MockResponse({
                "result": {
                    "id": "task-hist",
                    "status": {"state": "completed"},
                    "artifacts": [],
                    "history": [
                        {
                            "role": "agent",
                            "parts": [{"kind": "text", "text": "From history"}],
                        }
                    ],
                }
            })
        ]
        client = MockClient(responses)
        result = asyncio.get_event_loop().run_until_complete(
            send_message(client, "http://localhost:3773", "Test")
        )
        assert result == "From history"
