"""Tests for capabilities utilities."""

from unittest.mock import MagicMock
from bindu.utils.capabilities import (
    add_extension_to_capabilities,
    get_x402_extension_from_capabilities,
)
from bindu.extensions.x402 import X402AgentExtension


class TestAddExtensionToCapabilities:
    """Test adding extensions to capabilities."""

    def test_add_extension_to_none(self):
        """Test adding extension when capabilities is None."""
        mock_ext = MagicMock()
        result = add_extension_to_capabilities(None, mock_ext)
        assert result["extensions"] == [mock_ext]
        assert result["push_notifications"] is False
        assert result["streaming"] is False

    def test_add_extension_to_dict(self):
        """Test adding extension to existing dict."""
        mock_ext = MagicMock()
        capabilities = {"push_notifications": True, "streaming": False}
        result = add_extension_to_capabilities(capabilities, mock_ext)
        assert result["extensions"] == [mock_ext]
        assert result["push_notifications"] is True

    def test_add_extension_preserves_existing_extensions(self):
        """Test that existing extensions are preserved."""
        mock_ext1 = MagicMock()
        mock_ext2 = MagicMock()
        capabilities = {"extensions": [mock_ext1]}
        result = add_extension_to_capabilities(capabilities, mock_ext2)
        assert len(result["extensions"]) == 2
        assert mock_ext1 in result["extensions"]
        assert mock_ext2 in result["extensions"]

    def test_add_extension_non_dict_capabilities(self):
        """Test adding extension when capabilities is not a dict."""
        mock_ext = MagicMock()
        result = add_extension_to_capabilities(None, mock_ext)  # type: ignore[arg-type]
        assert result["extensions"] == [mock_ext]


class TestGetX402ExtensionFromCapabilities:
    """Test extracting X402 extension from capabilities."""

    def test_get_x402_extension_found(self):
        """Test finding X402 extension."""
        mock_x402 = X402AgentExtension(
            amount="1000000",
            token="USDC",
            network="base-sepolia",
            pay_to_address="0x123",
        )
        mock_manifest = MagicMock()
        mock_manifest.capabilities.get.return_value = [mock_x402]

        result = get_x402_extension_from_capabilities(mock_manifest)
        assert result is mock_x402

    def test_get_x402_extension_not_found(self):
        """Test when X402 extension is not present."""
        mock_manifest = MagicMock()
        mock_manifest.capabilities.get.return_value = []

        result = get_x402_extension_from_capabilities(mock_manifest)
        assert result is None
