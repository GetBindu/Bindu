"""Minimal tests for capability utilities."""

from bindu.utils.capabilities import (
    add_extension_to_capabilities,
    get_x402_extension_from_capabilities,
)


class TestCapabilityUtilities:
    """Test capability manipulation utilities."""

    def test_add_extension_to_capabilities(self):
        """Test adding extension to capabilities."""
        capabilities = {}
        extension_uri = "https://example.com/extension"

        result = add_extension_to_capabilities(capabilities, extension_uri)

        assert "extensions" in result
        assert extension_uri in result["extensions"]

    def test_add_extension_preserves_existing(self):
        """Test adding extension preserves existing extensions."""
        capabilities = {"extensions": ["https://existing.com/ext"]}
        new_uri = "https://new.com/ext"

        result = add_extension_to_capabilities(capabilities, new_uri)

        assert len(result["extensions"]) == 2
        assert "https://existing.com/ext" in result["extensions"]
        assert new_uri in result["extensions"]

    def test_get_x402_extension_found(self):
        """Test retrieving x402 extension when present."""
        from bindu.extensions.x402 import X402AgentExtension
        from unittest.mock import Mock

        x402_ext = X402AgentExtension(amount="1000000", pay_to_address="0x123")
        manifest = Mock()
        manifest.capabilities = {"extensions": [x402_ext, "other-ext"]}

        result = get_x402_extension_from_capabilities(manifest)

        assert result == x402_ext

    def test_get_x402_extension_not_found(self):
        """Test retrieving x402 extension when not present."""
        from unittest.mock import Mock

        manifest = Mock()
        manifest.capabilities = {"extensions": ["other-ext"]}

        result = get_x402_extension_from_capabilities(manifest)

        assert result is None

    def test_get_x402_extension_empty_capabilities(self):
        """Test retrieving x402 extension from empty capabilities."""
        from unittest.mock import Mock

        manifest = Mock()
        manifest.capabilities = {}

        result = get_x402_extension_from_capabilities(manifest)

        assert result is None
