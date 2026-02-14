"""Tests for hybrid authentication client."""

from pathlib import Path
from unittest.mock import MagicMock

from bindu.utils.hybrid_auth_client import HybridAuthClient


class TestHybridAuthClient:
    """Test hybrid authentication client."""

    def test_client_initialization(self):
        """Test client initialization sets attributes."""
        mock_did_ext = MagicMock()
        mock_did_ext.did = "did:key:test"

        client = HybridAuthClient(
            agent_id="test-agent",
            credentials_dir=Path("/tmp/.bindu"),
            did_extension=mock_did_ext,
        )

        assert client.agent_id == "test-agent"
        assert client.credentials_dir == Path("/tmp/.bindu")
        assert client.did_extension == mock_did_ext
        assert client.credentials is None
        assert client.access_token is None
