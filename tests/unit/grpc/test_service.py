"""Tests for BinduServiceImpl — gRPC registration service."""

import json
from unittest.mock import MagicMock, patch


from bindu.grpc.generated import agent_handler_pb2
from bindu.grpc.registry import AgentRegistry
from bindu.grpc.service import BinduServiceImpl, _proto_skills_to_dicts


class TestProtoSkillConversion:
    """Test proto SkillDefinition to dict conversion."""

    def test_basic_skill_conversion(self):
        """Test converting a proto SkillDefinition to a dict."""
        skill = agent_handler_pb2.SkillDefinition(
            name="research",
            description="Research capability",
            version="1.0.0",
            author="dev@example.com",
        )
        skill.tags.extend(["research", "search"])
        skill.input_modes.extend(["text/plain"])
        skill.output_modes.extend(["text/plain", "application/json"])

        result = _proto_skills_to_dicts([skill])

        assert len(result) == 1
        assert result[0]["name"] == "research"
        assert result[0]["description"] == "Research capability"
        assert result[0]["tags"] == ["research", "search"]
        assert result[0]["input_modes"] == ["text/plain"]
        assert result[0]["output_modes"] == ["text/plain", "application/json"]
        assert result[0]["version"] == "1.0.0"
        assert result[0]["author"] == "dev@example.com"

    def test_skill_with_raw_content(self):
        """Test that raw_content and format are preserved."""
        skill = agent_handler_pb2.SkillDefinition(
            name="echo",
            description="Echo skill",
            raw_content="name: echo\ndescription: Echo skill",
            format="yaml",
        )

        result = _proto_skills_to_dicts([skill])

        assert result[0]["raw_content"] == "name: echo\ndescription: Echo skill"
        assert result[0]["format"] == "yaml"

    def test_empty_skills_list(self):
        """Test converting empty skills list."""
        assert _proto_skills_to_dicts([]) == []

    def test_multiple_skills(self):
        """Test converting multiple skills."""
        skills = [
            agent_handler_pb2.SkillDefinition(name="a", description="A"),
            agent_handler_pb2.SkillDefinition(name="b", description="B"),
        ]
        result = _proto_skills_to_dicts(skills)
        assert len(result) == 2
        assert result[0]["name"] == "a"
        assert result[1]["name"] == "b"


class TestBinduServiceImpl:
    """Test BinduService gRPC implementation."""

    def test_register_agent_invalid_json(self):
        """Test RegisterAgent with invalid JSON config."""
        registry = AgentRegistry()
        service = BinduServiceImpl(registry)
        context = MagicMock()

        request = agent_handler_pb2.RegisterAgentRequest(
            config_json="not valid json",
            grpc_callback_address="localhost:50052",
        )

        response = service.RegisterAgent(request, context)
        assert response.success is False
        assert "Invalid config_json" in response.error

    @patch("bindu.penguin.bindufy._bindufy_core")
    def test_register_agent_success(self, mock_bindufy_core):
        """Test successful agent registration via gRPC."""
        # Mock the manifest returned by _bindufy_core
        mock_manifest = MagicMock()
        mock_manifest.id = "test-agent-id-123"
        mock_manifest.url = "http://localhost:3773"
        mock_manifest.did_extension.did = "did:key:z6Mk..."
        mock_bindufy_core.return_value = mock_manifest

        registry = AgentRegistry()
        service = BinduServiceImpl(registry)
        context = MagicMock()

        config = {
            "author": "dev@example.com",
            "name": "test-agent",
            "description": "A test agent",
            "deployment": {"url": "http://localhost:3773", "expose": True},
        }

        request = agent_handler_pb2.RegisterAgentRequest(
            config_json=json.dumps(config),
            grpc_callback_address="localhost:50052",
        )

        response = service.RegisterAgent(request, context)

        assert response.success is True
        assert response.agent_id == "test-agent-id-123"
        assert response.did == "did:key:z6Mk..."
        assert response.agent_url == "http://localhost:3773"

        # Verify _bindufy_core was called with correct args
        mock_bindufy_core.assert_called_once()
        call_kwargs = mock_bindufy_core.call_args[1]
        assert call_kwargs["skip_handler_validation"] is True
        assert call_kwargs["run_server_in_background"] is True

    @patch("bindu.penguin.bindufy._bindufy_core")
    def test_register_agent_failure(self, mock_bindufy_core):
        """Test RegisterAgent when _bindufy_core raises an exception."""
        mock_bindufy_core.side_effect = ValueError("Missing required field")

        registry = AgentRegistry()
        service = BinduServiceImpl(registry)
        context = MagicMock()

        config = {"name": "bad-agent"}
        request = agent_handler_pb2.RegisterAgentRequest(
            config_json=json.dumps(config),
            grpc_callback_address="localhost:50052",
        )

        response = service.RegisterAgent(request, context)
        assert response.success is False
        assert "Registration failed" in response.error

    def test_heartbeat_known_agent(self):
        """Test heartbeat for a registered agent."""
        registry = AgentRegistry()
        manifest = MagicMock()
        registry.register("agent-1", "localhost:50052", manifest)

        service = BinduServiceImpl(registry)
        context = MagicMock()

        request = agent_handler_pb2.HeartbeatRequest(
            agent_id="agent-1", timestamp=1234567890
        )
        response = service.Heartbeat(request, context)

        assert response.acknowledged is True
        assert response.server_timestamp > 0

    def test_heartbeat_unknown_agent(self):
        """Test heartbeat for unknown agent."""
        registry = AgentRegistry()
        service = BinduServiceImpl(registry)
        context = MagicMock()

        request = agent_handler_pb2.HeartbeatRequest(
            agent_id="unknown", timestamp=1234567890
        )
        response = service.Heartbeat(request, context)

        assert response.acknowledged is False

    def test_unregister_known_agent(self):
        """Test unregistering a known agent."""
        registry = AgentRegistry()
        manifest = MagicMock()
        manifest.run = MagicMock()
        manifest.run.close = MagicMock()
        registry.register("agent-1", "localhost:50052", manifest)

        service = BinduServiceImpl(registry)
        context = MagicMock()

        request = agent_handler_pb2.UnregisterAgentRequest(agent_id="agent-1")
        response = service.UnregisterAgent(request, context)

        assert response.success is True
        assert registry.get("agent-1") is None
        manifest.run.close.assert_called_once()

    def test_unregister_unknown_agent(self):
        """Test unregistering unknown agent."""
        registry = AgentRegistry()
        service = BinduServiceImpl(registry)
        context = MagicMock()

        request = agent_handler_pb2.UnregisterAgentRequest(agent_id="unknown")
        response = service.UnregisterAgent(request, context)

        assert response.success is False
        assert "not found" in response.error
