"""Tests for the gRPC agent registry."""

from unittest.mock import MagicMock


from bindu.grpc.registry import AgentRegistry, RegisteredAgent


class TestAgentRegistry:
    """Test thread-safe agent registry operations."""

    def _make_mock_manifest(self, name: str = "test-agent") -> MagicMock:
        """Create a mock AgentManifest for testing."""
        manifest = MagicMock()
        manifest.name = name
        manifest.id = "test-id-123"
        return manifest

    def test_register_and_get(self):
        """Test registering and retrieving an agent."""
        registry = AgentRegistry()
        manifest = self._make_mock_manifest()

        entry = registry.register("agent-1", "localhost:50052", manifest)

        assert isinstance(entry, RegisteredAgent)
        assert entry.agent_id == "agent-1"
        assert entry.grpc_callback_address == "localhost:50052"
        assert entry.manifest is manifest

        retrieved = registry.get("agent-1")
        assert retrieved is entry

    def test_get_unknown_agent(self):
        """Test that looking up unknown agent returns None."""
        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    def test_unregister(self):
        """Test unregistering an agent."""
        registry = AgentRegistry()
        manifest = self._make_mock_manifest()
        registry.register("agent-1", "localhost:50052", manifest)

        assert registry.unregister("agent-1") is True
        assert registry.get("agent-1") is None

    def test_unregister_unknown(self):
        """Test unregistering unknown agent returns False."""
        registry = AgentRegistry()
        assert registry.unregister("nonexistent") is False

    def test_update_heartbeat(self):
        """Test heartbeat updates the timestamp."""
        registry = AgentRegistry()
        manifest = self._make_mock_manifest()
        entry = registry.register("agent-1", "localhost:50052", manifest)

        old_heartbeat = entry.last_heartbeat
        assert registry.update_heartbeat("agent-1") is True

        updated = registry.get("agent-1")
        assert updated is not None
        assert updated.last_heartbeat >= old_heartbeat

    def test_update_heartbeat_unknown(self):
        """Test heartbeat for unknown agent returns False."""
        registry = AgentRegistry()
        assert registry.update_heartbeat("nonexistent") is False

    def test_list_agents(self):
        """Test listing all registered agents."""
        registry = AgentRegistry()
        m1 = self._make_mock_manifest("agent-a")
        m2 = self._make_mock_manifest("agent-b")

        registry.register("a", "localhost:50052", m1)
        registry.register("b", "localhost:50053", m2)

        agents = registry.list_agents()
        assert len(agents) == 2
        agent_ids = {a.agent_id for a in agents}
        assert agent_ids == {"a", "b"}

    def test_list_agents_empty(self):
        """Test listing when no agents registered."""
        registry = AgentRegistry()
        assert registry.list_agents() == []

    def test_len(self):
        """Test registry length."""
        registry = AgentRegistry()
        assert len(registry) == 0

        manifest = self._make_mock_manifest()
        registry.register("agent-1", "localhost:50052", manifest)
        assert len(registry) == 1

        registry.unregister("agent-1")
        assert len(registry) == 0

    def test_register_replaces_existing(self):
        """Test that re-registering overwrites the previous entry."""
        registry = AgentRegistry()
        m1 = self._make_mock_manifest("v1")
        m2 = self._make_mock_manifest("v2")

        registry.register("agent-1", "localhost:50052", m1)
        registry.register("agent-1", "localhost:50053", m2)

        entry = registry.get("agent-1")
        assert entry is not None
        assert entry.grpc_callback_address == "localhost:50053"
        assert entry.manifest.name == "v2"
        assert len(registry) == 1
