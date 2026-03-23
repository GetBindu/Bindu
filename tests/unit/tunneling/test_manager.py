"""Minimal tests for TunnelManager."""

from unittest.mock import Mock, patch
import pytest

from bindu.tunneling.manager import TunnelManager


class TestTunnelManager:
    """Test TunnelManager functionality."""

    def test_manager_initialization(self):
        """Test manager initializes with no active tunnel."""
        manager = TunnelManager()

        assert manager.active_tunnel is None

    @patch("bindu.tunneling.manager.Tunnel")
    def test_create_tunnel_success(self, mock_tunnel_class):
        """Test successful tunnel creation."""
        mock_tunnel = Mock()
        mock_tunnel.start.return_value = "https://test.example.com"
        mock_tunnel_class.return_value = mock_tunnel

        manager = TunnelManager()
        url = manager.create_tunnel(local_port=8080, subdomain="test")

        assert url == "https://test.example.com"
        assert manager.active_tunnel == mock_tunnel
        mock_tunnel.start.assert_called_once()

    @patch("bindu.tunneling.manager.Tunnel")
    def test_create_tunnel_when_already_active_raises(self, mock_tunnel_class):
        """Test that creating tunnel when one is active raises error."""
        mock_tunnel = Mock()
        mock_tunnel.start.return_value = "https://test.example.com"
        mock_tunnel_class.return_value = mock_tunnel

        manager = TunnelManager()
        manager.create_tunnel(local_port=8080, subdomain="test")

        with pytest.raises(RuntimeError, match="already active"):
            manager.create_tunnel(local_port=9090, subdomain="test2")

    def test_stop_tunnel_when_active(self):
        """Test stopping active tunnel."""
        manager = TunnelManager()
        mock_tunnel = Mock()
        manager.active_tunnel = mock_tunnel

        manager.stop_tunnel()

        mock_tunnel.stop.assert_called_once()
        assert manager.active_tunnel is None

    def test_stop_tunnel_when_none_active(self):
        """Test stopping tunnel when none is active."""
        manager = TunnelManager()

        # Should not raise
        manager.stop_tunnel()

        assert manager.active_tunnel is None

    @patch("bindu.tunneling.manager.Tunnel")
    def test_generate_subdomain_used_when_none_provided(self, mock_tunnel_class):
        """Test that subdomain is auto-generated when not provided."""
        mock_tunnel = Mock()
        mock_tunnel.start.return_value = "https://auto.example.com"
        mock_tunnel_class.return_value = mock_tunnel

        manager = TunnelManager()
        manager.create_tunnel(local_port=8080)

        # Verify tunnel was created with a config that has a subdomain
        call_args = mock_tunnel_class.call_args
        config = call_args[0][0]
        assert config.subdomain is not None
        assert len(config.subdomain) > 0
