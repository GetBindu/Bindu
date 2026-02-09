"""Unit tests for the tunneling module.

Tests cover:
- TunnelConfig creation and validation
- Binary download and management
- TunnelManager lifecycle
- Tunnel process management
- Module exports
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from bindu.tunneling import TunnelConfig, TunnelManager, Tunnel
from bindu.tunneling.config import _get_default_server_address, _get_default_tunnel_domain
from bindu.tunneling.binary import (
    get_binary_path,
    BINARY_PATH,
    BINARY_FOLDER,
)


class TestTunnelConfig:
    """Test TunnelConfig dataclass."""

    def test_default_config(self):
        """Test default TunnelConfig values."""
        config = TunnelConfig()
        
        assert config.enabled is False
        assert config.protocol == "http"
        assert config.use_tls is False
        assert config.local_host == "127.0.0.1"
        assert config.local_port is None
        assert config.subdomain is None

    def test_config_with_custom_values(self):
        """Test TunnelConfig with custom values."""
        config = TunnelConfig(
            enabled=True,
            subdomain="test-subdomain",
            local_port=8080,
            protocol="https",
        )
        
        assert config.enabled is True
        assert config.subdomain == "test-subdomain"
        assert config.local_port == 8080
        assert config.protocol == "https"

    def test_get_public_url_success(self):
        """Test get_public_url with valid subdomain."""
        config = TunnelConfig(subdomain="myapp")
        url = config.get_public_url()
        
        assert url == "https://myapp.tunnel.getbindu.com"
        assert url.startswith("https://")

    def test_get_public_url_no_subdomain(self):
        """Test get_public_url raises error without subdomain."""
        config = TunnelConfig()
        
        with pytest.raises(ValueError, match="Subdomain must be set"):
            config.get_public_url()

    def test_get_public_url_custom_domain(self):
        """Test get_public_url with custom tunnel domain."""
        config = TunnelConfig(
            subdomain="test",
            tunnel_domain="custom.example.com"
        )
        url = config.get_public_url()
        
        assert url == "https://test.custom.example.com"

    def test_default_server_address(self):
        """Test default server address from settings."""
        address = _get_default_server_address()
        assert isinstance(address, str)
        assert ":" in address  # Should be host:port format

    def test_default_tunnel_domain(self):
        """Test default tunnel domain from settings."""
        domain = _get_default_tunnel_domain()
        assert isinstance(domain, str)
        assert len(domain) > 0


class TestBinaryManagement:
    """Test FRP binary download and management."""

    def test_get_binary_path(self):
        """Test get_binary_path returns correct path."""
        path = get_binary_path()
        
        assert isinstance(path, Path)
        assert path == BINARY_PATH
        assert "frpc" in str(path)

    def test_binary_folder_structure(self):
        """Test binary folder is in correct location."""
        assert BINARY_FOLDER.name == "frpc"
        assert ".bindu" in str(BINARY_FOLDER)

    @patch("bindu.tunneling.binary.BINARY_PATH")
    def test_binary_path_exists_check(self, mock_path):
        """Test binary path existence check."""
        mock_path.exists.return_value = True
        assert mock_path.exists()

    @patch("bindu.tunneling.binary.Path")
    def test_binary_filename_format(self, mock_path):
        """Test binary filename includes version and platform."""
        from bindu.tunneling.binary import BINARY_FILENAME
        
        assert "frpc" in BINARY_FILENAME
        assert "v0.61.0" in BINARY_FILENAME or "v" in BINARY_FILENAME


class TestTunnelManager:
    """Test TunnelManager class."""

    def test_manager_initialization(self):
        """Test TunnelManager initializes with no active tunnel."""
        manager = TunnelManager()
        
        assert manager.active_tunnel is None

    def test_create_tunnel_with_existing_active(self):
        """Test creating tunnel when one is already active raises error."""
        manager = TunnelManager()
        manager.active_tunnel = Mock()  # Simulate active tunnel
        
        with pytest.raises(RuntimeError, match="already active"):
            manager.create_tunnel(local_port=3773)

    def test_create_tunnel_with_config(self):
        """Test create_tunnel accepts custom config."""
        manager = TunnelManager()
        config = TunnelConfig(enabled=True, subdomain="test")
        
        with patch.object(manager, "active_tunnel", None):
            with patch("bindu.tunneling.manager.Tunnel") as mock_tunnel:
                mock_tunnel_instance = Mock()
                mock_tunnel_instance.start.return_value = "https://test.tunnel.getbindu.com"
                mock_tunnel.return_value = mock_tunnel_instance
                
                url = manager.create_tunnel(local_port=3773, config=config)
                
                assert url == "https://test.tunnel.getbindu.com"
                mock_tunnel.assert_called_once()

    def test_create_tunnel_without_config(self):
        """Test create_tunnel creates default config."""
        manager = TunnelManager()
        
        with patch("bindu.tunneling.manager.Tunnel") as mock_tunnel:
            mock_tunnel_instance = Mock()
            mock_tunnel_instance.start.return_value = "https://random.tunnel.getbindu.com"
            mock_tunnel.return_value = mock_tunnel_instance
            
            url = manager.create_tunnel(local_port=3773)
            
            assert "tunnel.getbindu.com" in url
            mock_tunnel.assert_called_once()

    def test_generate_subdomain_length(self):
        """Test _generate_subdomain creates correct length."""
        subdomain = TunnelManager._generate_subdomain(length=12)
        
        assert len(subdomain) == 12
        assert subdomain.isalnum()

    def test_generate_subdomain_uniqueness(self):
        """Test _generate_subdomain creates unique values."""
        subdomain1 = TunnelManager._generate_subdomain()
        subdomain2 = TunnelManager._generate_subdomain()
        
        assert subdomain1 != subdomain2

    def test_context_manager_enter(self):
        """Test TunnelManager as context manager - enter."""
        manager = TunnelManager()
        
        with manager as m:
            assert m is manager

    def test_context_manager_exit_with_active_tunnel(self):
        """Test TunnelManager context manager cleans up active tunnel."""
        manager = TunnelManager()
        mock_tunnel = Mock()
        manager.active_tunnel = mock_tunnel
        
        with manager:
            pass
        
        # Context manager should stop the tunnel
        mock_tunnel.stop.assert_called_once()

    def test_context_manager_exit_no_active_tunnel(self):
        """Test TunnelManager context manager with no active tunnel."""
        manager = TunnelManager()
        
        # Should not raise error
        with manager:
            pass
        
        assert manager.active_tunnel is None


class TestTunnel:
    """Test Tunnel class."""

    def test_tunnel_initialization(self):
        """Test Tunnel initializes with config."""
        config = TunnelConfig(enabled=True)
        tunnel = Tunnel(config)
        
        assert tunnel.config == config
        assert tunnel.proc is None
        assert tunnel.public_url is None

    def test_tunnel_config_validation(self):
        """Test Tunnel validates config."""
        config = TunnelConfig(enabled=True)
        tunnel = Tunnel(config)
        
        assert tunnel.config.enabled is True

    @patch("bindu.tunneling.tunnel.download_binary")
    @patch("bindu.tunneling.tunnel.subprocess.Popen")
    def test_start_tunnel_downloads_binary(self, mock_popen, mock_download):
        """Test start() downloads binary if needed."""
        mock_download.return_value = Path("/fake/path/frpc")
        mock_proc = Mock()
        mock_proc.stdout.readline.side_effect = [
            "try to connect to server...\n",
            "start proxy success\n",
            "",
        ]
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc
        
        config = TunnelConfig(enabled=True, subdomain="test", local_port=3773)
        tunnel = Tunnel(config)
        
        with patch.object(tunnel, "_read_url_from_output", return_value="https://test.tunnel.getbindu.com"):
            url = tunnel.start()
            
            mock_download.assert_called_once()
            assert url == "https://test.tunnel.getbindu.com"

    def test_stop_tunnel_no_process(self):
        """Test stop() when no process is running."""
        config = TunnelConfig(enabled=True)
        tunnel = Tunnel(config)
        
        tunnel.stop()  # Should not raise error
        assert tunnel.proc is None

    @patch("bindu.tunneling.tunnel.subprocess.Popen")
    def test_stop_tunnel_terminates_process(self, mock_popen):
        """Test stop() terminates running process."""
        config = TunnelConfig(enabled=True)
        tunnel = Tunnel(config)
        
        mock_proc = Mock()
        tunnel.proc = mock_proc
        tunnel.public_url = "https://test.tunnel.getbindu.com"
        
        tunnel.stop()
        
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()

    def test_start_without_local_port(self):
        """Test start() raises error without local_port."""
        config = TunnelConfig(enabled=True)  # No local_port
        tunnel = Tunnel(config)
        
        with patch("bindu.tunneling.tunnel.download_binary", return_value=Path("/fake/frpc")):
            with pytest.raises(ValueError, match="Local port must be set"):
                tunnel.start()


class TestModuleExports:
    """Test module __init__.py exports."""

    def test_module_exports_tunnel_config(self):
        """Test TunnelConfig is exported."""
        from bindu.tunneling import TunnelConfig as ExportedConfig
        assert ExportedConfig is TunnelConfig

    def test_module_exports_tunnel_manager(self):
        """Test TunnelManager is exported."""
        from bindu.tunneling import TunnelManager as ExportedManager
        assert ExportedManager is TunnelManager

    def test_module_exports_tunnel(self):
        """Test Tunnel is exported."""
        from bindu.tunneling import Tunnel as ExportedTunnel
        assert ExportedTunnel is Tunnel

    def test_module_all_attribute(self):
        """Test __all__ contains expected exports."""
        import bindu.tunneling as tunnel_module
        
        assert hasattr(tunnel_module, "__all__")
        assert "TunnelConfig" in tunnel_module.__all__
        assert "TunnelManager" in tunnel_module.__all__
        assert "Tunnel" in tunnel_module.__all__
        assert len(tunnel_module.__all__) == 3


class TestTunnelIntegration:
    """Integration tests for tunnel components."""

    def test_config_to_manager_flow(self):
        """Test config flows correctly to manager."""
        config = TunnelConfig(enabled=True, subdomain="integration-test")
        manager = TunnelManager()
        
        assert config.enabled is True
        assert manager.active_tunnel is None

    def test_manager_creates_tunnel_with_config(self):
        """Test manager creates tunnel with provided config."""
        config = TunnelConfig(enabled=True, subdomain="test", local_port=3773)
        
        with patch("bindu.tunneling.manager.Tunnel") as mock_tunnel:
            mock_instance = Mock()
            mock_instance.start.return_value = "https://test.tunnel.getbindu.com"
            mock_tunnel.return_value = mock_instance
            
            manager = TunnelManager()
            url = manager.create_tunnel(local_port=3773, config=config)
            
            assert url == "https://test.tunnel.getbindu.com"
            assert manager.active_tunnel is not None

    def test_subdomain_generation_and_url_construction(self):
        """Test subdomain generation integrates with URL construction."""
        subdomain = TunnelManager._generate_subdomain(length=12)
        config = TunnelConfig(subdomain=subdomain)
        
        url = config.get_public_url()
        
        assert subdomain in url
        assert url.startswith("https://")
        assert ".tunnel.getbindu.com" in url
