"""Minimal tests for response detector."""

import json

from bindu.server.workers.helpers.response_detector import ResponseDetector


class TestResponseDetector:
    """Test response detector functionality."""

    def test_parse_structured_response_with_dict(self):
        """Test parsing dict with state key."""
        result = {"state": "input-required", "prompt": "Enter password"}

        parsed = ResponseDetector.parse_structured_response(result)

        assert parsed is not None
        assert parsed["state"] == "input-required"
        assert parsed["prompt"] == "Enter password"

    def test_parse_structured_response_dict_without_state(self):
        """Test parsing dict without state key returns None."""
        result = {"message": "Hello", "data": "test"}

        parsed = ResponseDetector.parse_structured_response(result)

        assert parsed is None

    def test_parse_structured_response_with_json_string(self):
        """Test parsing JSON string."""
        result = json.dumps({"state": "auth-required", "prompt": "Login needed"})

        parsed = ResponseDetector.parse_structured_response(result)

        assert parsed is not None
        assert parsed["state"] == "auth-required"

    def test_parse_structured_response_with_plain_string(self):
        """Test parsing plain string returns None."""
        result = "This is just a plain text response"

        parsed = ResponseDetector.parse_structured_response(result)

        assert parsed is None

    def test_parse_structured_response_with_list(self):
        """Test parsing list returns None."""
        result = ["message1", "message2"]

        parsed = ResponseDetector.parse_structured_response(result)

        assert parsed is None

    def test_parse_structured_response_with_none(self):
        """Test parsing None returns None."""
        parsed = ResponseDetector.parse_structured_response(None)

        assert parsed is None

    def test_determine_task_state_input_required(self):
        """Test determining input-required state."""
        result = "Some result"
        structured = {"state": "input-required", "prompt": "Enter data"}

        state, content = ResponseDetector.determine_task_state(result, structured)

        assert state == "input-required"
        assert content == "Enter data"

    def test_determine_task_state_auth_required(self):
        """Test determining auth-required state."""
        result = "Some result"
        structured = {"state": "auth-required", "prompt": "Login"}

        state, content = ResponseDetector.determine_task_state(result, structured)

        assert state == "auth-required"
        assert content == "Login"

    def test_determine_task_state_completed(self):
        """Test determining completed state for None structured."""
        result = "Task completed successfully"

        state, content = ResponseDetector.determine_task_state(result, None)

        assert state == "completed"
        assert content == "Task completed successfully"

    def test_determine_task_state_unknown_defaults_to_completed(self):
        """Test unknown state defaults to completed."""
        result = "Result"
        structured = {"state": "unknown-state"}

        state, content = ResponseDetector.determine_task_state(result, structured)

        assert state == "completed"

    def test_parse_structured_response_with_invalid_json(self):
        """Test parsing invalid JSON string returns None."""
        result = "not valid json {{"

        parsed = ResponseDetector.parse_structured_response(result)

        assert parsed is None

    def test_determine_task_state_with_prompt_field(self):
        """Test determining state extracts prompt field."""
        result = "Some result"
        structured = {"state": "input-required", "prompt": "Enter your name"}

        state, content = ResponseDetector.determine_task_state(result, structured)

        assert state == "input-required"
        assert content == "Enter your name"

    def test_determine_task_state_without_prompt_uses_result(self):
        """Test determining state without prompt uses result."""
        result = "Task result"
        structured = {"state": "completed"}

        state, content = ResponseDetector.determine_task_state(result, structured)

        assert state == "completed"
        assert content == "Task result"
