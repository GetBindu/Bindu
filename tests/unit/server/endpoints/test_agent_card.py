"""Minimal tests for agent card utilities."""

from unittest.mock import Mock

from bindu.server.endpoints.agent_card import (
    _serialize_extension,
    _serialize_extensions,
)


class TestAgentCardUtilities:
    """Test agent card utility functions."""

    def test_serialize_extension_did_type(self):
        """Test serializing DID extension."""
        mock_ext = Mock()
        mock_ext.did = "bindu:test:agent"
        mock_ext.author = "test@example.com"
        mock_ext.agent_name = "Test Agent"
        mock_ext.agent_id = "test-id"

        result = _serialize_extension(mock_ext)

        assert result is not None
        assert result["uri"] == "did:bindu:test:agent"
        assert result["params"]["author"] == "test@example.com"
        assert result["required"] is False

    def test_serialize_extension_dict_type(self):
        """Test serializing dict extension."""
        ext_dict = {"uri": "https://example.com/ext", "required": True}

        result = _serialize_extension(ext_dict)

        assert result == ext_dict

    def test_serialize_extension_unknown_type(self):
        """Test serializing unknown extension type returns None."""
        result = _serialize_extension("invalid")

        assert result is None

    def test_serialize_extensions_in_place(self):
        """Test serializing extensions list in capabilities."""
        mock_ext = Mock()
        mock_ext.did = "bindu:test"
        mock_ext.author = "test@example.com"
        mock_ext.agent_name = "Test"
        mock_ext.agent_id = "123"

        capabilities = {"extensions": [mock_ext, "invalid"]}

        _serialize_extensions(capabilities)

        assert len(capabilities["extensions"]) == 1
        first_ext = capabilities["extensions"][0]
        assert isinstance(first_ext, dict)
        assert first_ext["uri"] == "did:bindu:test"
