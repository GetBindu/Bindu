"""Minimal focused tests for DID setup."""

from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4
import pytest

from bindu.penguin.did_setup import initialize_did_extension


class TestInitializeDIDExtension:
    """Test DID extension initialization."""

    @patch("bindu.penguin.did_setup.app_settings")
    @patch("bindu.penguin.did_setup.DIDAgentExtension")
    def test_initialize_creates_did_extension(self, mock_did_class, mock_settings):
        """Test DID extension is created successfully."""
        mock_settings.vault.enabled = False
        mock_settings.did.pki_dir = "pki"

        mock_instance = Mock()
        mock_instance.did = "did:bindu:test:agent"
        mock_did_class.return_value = mock_instance

        result = initialize_did_extension(
            agent_id=uuid4(),
            author="test@example.com",
            agent_name="test-agent",
            key_dir=Path("/tmp/keys"),
        )

        assert result == mock_instance
        mock_did_class.assert_called_once()

    @patch("bindu.penguin.did_setup.app_settings")
    @patch("bindu.penguin.did_setup.DIDAgentExtension")
    def test_initialize_with_recreate_keys(self, mock_did_class, mock_settings):
        """Test DID initialization with recreate_keys flag."""
        mock_settings.vault.enabled = False
        mock_settings.did.pki_dir = "pki"

        mock_instance = Mock()
        mock_instance.did = "did:bindu:test:agent"
        mock_did_class.return_value = mock_instance

        initialize_did_extension(
            agent_id=uuid4(),
            author="test@example.com",
            agent_name="test-agent",
            key_dir=Path("/tmp/keys"),
            recreate_keys=True,
        )

        call_kwargs = mock_did_class.call_args.kwargs
        assert call_kwargs["recreate_keys"] is True

    @patch("bindu.penguin.did_setup.app_settings")
    @patch("bindu.penguin.did_setup.DIDAgentExtension")
    def test_initialize_integrity_check_failure_raises(
        self, mock_did_class, mock_settings
    ):
        """Test that integrity check failure raises error."""
        mock_settings.vault.enabled = False
        mock_settings.did.pki_dir = "pki"

        mock_instance = Mock()
        mock_instance.check_integrity.side_effect = ValueError("Integrity check failed")
        mock_did_class.return_value = mock_instance

        with pytest.raises(ValueError, match="Integrity check failed"):
            initialize_did_extension(
                agent_id=uuid4(),
                author="test@example.com",
                agent_name="test-agent",
                key_dir=Path("/tmp/keys"),
            )
