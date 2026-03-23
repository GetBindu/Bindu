"""Minimal tests for health endpoint utilities."""

from unittest.mock import Mock

from bindu.server.endpoints.health import _build_health_payload


class TestHealthUtilities:
    """Test health endpoint utility functions."""

    def test_build_health_payload_structure(self):
        """Test building health payload structure."""
        mock_app = Mock()
        mock_app.penguin_id = "test-penguin-123"

        runtime = {
            "storage_type": "memory",
            "scheduler_type": "memory",
            "task_manager_running": True,
            "strict_ready": True,
        }

        payload = _build_health_payload(mock_app, runtime, "did:bindu:test")

        assert "version" in payload
        assert payload["health"] == "healthy"
        assert payload["runtime"]["storage_backend"] == "memory"
        assert payload["application"]["penguin_id"] == "test-penguin-123"
        assert payload["application"]["agent_did"] == "did:bindu:test"

    def test_build_health_payload_degraded(self):
        """Test building health payload when degraded."""
        mock_app = Mock()
        mock_app.penguin_id = "test-penguin-456"

        runtime = {
            "storage_type": "memory",
            "scheduler_type": "memory",
            "task_manager_running": False,
            "strict_ready": False,
        }

        payload = _build_health_payload(mock_app, runtime, None)

        assert payload["health"] == "degraded"
        assert payload["runtime"]["strict_ready"] is False
        assert payload["application"]["agent_did"] is None
