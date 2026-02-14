"""Tests for DID setup utilities."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from bindu.penguin.did_setup import initialize_did_extension


class TestInitializeDIDExtension:
    """Test DID extension initialization."""

    @patch("bindu.penguin.did_setup.DIDAgentExtension")
    def test_initialize_did_extension_success(self, mock_did_class):
        """Test successful DID extension initialization."""
        mock_extension = MagicMock()
        mock_extension.did = "did:key:test123"
        mock_did_class.return_value = mock_extension

        result = initialize_did_extension(
            agent_id="agent-123",
            author="test@example.com",
            agent_name="Test Agent",
            key_dir=Path("/tmp/test"),
            recreate_keys=True,
            key_password="password123",  # pragma: allowlist secret
        )

        assert result is mock_extension
        mock_extension.generate_and_save_key_pair.assert_called_once()

    @patch("bindu.penguin.did_setup.DIDAgentExtension")
    def test_initialize_did_extension_failure(self, mock_did_class):
        """Test DID extension initialization failure."""
        mock_did_class.side_effect = Exception("Key generation failed")

        with pytest.raises(Exception, match="Key generation failed"):
            initialize_did_extension(
                agent_id="agent-123",
                author="test@example.com",
                agent_name="Test Agent",
                key_dir=Path("/tmp/test"),
            )

    @patch("bindu.penguin.did_setup.DIDAgentExtension")
    def test_initialize_did_extension_without_password(self, mock_did_class):
        """Test DID extension initialization without password."""
        mock_extension = MagicMock()
        mock_extension.did = "did:key:test123"
        mock_did_class.return_value = mock_extension

        result = initialize_did_extension(
            agent_id="agent-123",
            author=None,
            agent_name="Test Agent",
            key_dir=Path("/tmp/test"),
            recreate_keys=False,
        )

        assert result is mock_extension
        mock_did_class.assert_called_once()
        call_kwargs = mock_did_class.call_args[1]
        assert call_kwargs["recreate_keys"] is False
        assert call_kwargs["key_password"] is None
