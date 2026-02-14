"""Simplified tests for Hydra client."""

from bindu.auth.hydra.client import HydraClient


class TestHydraClient:
    """Test Hydra client initialization."""

    def test_client_initialization(self):
        """Test client initialization with URLs."""
        client = HydraClient(
            admin_url="https://hydra-admin.example.com",
            public_url="https://hydra.example.com",
        )

        assert client.admin_url == "https://hydra-admin.example.com"
        assert client.public_url == "https://hydra.example.com"

    def test_client_url_trailing_slash_stripped(self):
        """Test that trailing slashes are stripped from URLs."""
        client = HydraClient(
            admin_url="https://hydra-admin.example.com/",
            public_url="https://hydra.example.com/",
        )

        assert client.admin_url == "https://hydra-admin.example.com"
        assert client.public_url == "https://hydra.example.com"
