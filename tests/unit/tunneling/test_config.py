"""Minimal tests for TunnelConfig."""

import pytest

from bindu.tunneling.config import TunnelConfig


class TestTunnelConfig:
    """Test TunnelConfig dataclass."""

    def test_default_config_creation(self):
        """Test creating config with defaults."""
        config = TunnelConfig()

        assert config.enabled is False
        assert config.protocol == "http"
        assert config.use_tls is False
        assert config.local_host == "127.0.0.1"
        assert config.local_port is None

    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = TunnelConfig(
            enabled=True, subdomain="my-app", local_port=8080, use_tls=True
        )

        assert config.enabled is True
        assert config.subdomain == "my-app"
        assert config.local_port == 8080
        assert config.use_tls is True

    def test_get_public_url_success(self):
        """Test generating public URL with subdomain."""
        config = TunnelConfig(subdomain="test-app", tunnel_domain="example.com")

        url = config.get_public_url()

        assert url == "https://test-app.example.com"

    def test_get_public_url_without_subdomain_raises(self):
        """Test that public URL generation fails without subdomain."""
        config = TunnelConfig(subdomain=None)

        with pytest.raises(ValueError, match="Subdomain must be set"):
            config.get_public_url()
