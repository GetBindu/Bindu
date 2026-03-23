"""Comprehensive tests for settings preparation utilities."""

from unittest.mock import patch

from bindu.utils.config.settings import (
    prepare_auth_settings,
    prepare_vault_settings,
    update_auth_settings,
    update_vault_settings,
)


class TestPrepareAuthSettings:
    """Test auth settings preparation."""

    def test_prepare_auth_disabled(self):
        """Test when auth is disabled."""
        auth_config = {"enabled": False}

        result = prepare_auth_settings(auth_config)

        assert result is None

    def test_prepare_auth_not_configured(self):
        """Test when auth config is None."""
        result = prepare_auth_settings({})

        assert result is None

    def test_prepare_auth_empty_config(self):
        """Test when auth config is empty."""
        result = prepare_auth_settings({})

        assert result is None

    def test_prepare_auth_hydra_basic(self):
        """Test preparing basic Hydra auth settings."""
        auth_config = {
            "enabled": True,
            "provider": "hydra",
            "admin_url": "http://localhost:4445",
            "public_url": "http://localhost:4444",
        }

        result = prepare_auth_settings(auth_config)

        assert result is not None
        assert result["auth"]["enabled"] is True
        assert result["auth"]["provider"] == "hydra"
        assert result["hydra"]["admin_url"] == "http://localhost:4445"
        assert result["hydra"]["public_url"] == "http://localhost:4444"

    def test_prepare_auth_hydra_connection_settings(self):
        """Test preparing Hydra connection settings."""
        auth_config = {
            "enabled": True,
            "provider": "hydra",
            "timeout": 30,
            "verify_ssl": False,
            "max_retries": 3,
        }

        result = prepare_auth_settings(auth_config)

        assert result is not None
        assert result["hydra"]["timeout"] == 30
        assert result["hydra"]["verify_ssl"] is False
        assert result["hydra"]["max_retries"] == 3

    def test_prepare_auth_hydra_cache_settings(self):
        """Test preparing Hydra cache settings."""
        auth_config = {
            "enabled": True,
            "provider": "hydra",
            "cache_ttl": 300,
            "max_cache_size": 1000,
        }

        result = prepare_auth_settings(auth_config)

        assert result is not None
        assert result["hydra"]["cache_ttl"] == 300
        assert result["hydra"]["max_cache_size"] == 1000

    def test_prepare_auth_hydra_auto_register_settings(self):
        """Test preparing Hydra auto-registration settings."""
        auth_config = {
            "enabled": True,
            "provider": "hydra",
            "auto_register_agents": True,
            "agent_client_prefix": "bindu-agent-",
        }

        result = prepare_auth_settings(auth_config)

        assert result is not None
        assert result["hydra"]["auto_register_agents"] is True
        assert result["hydra"]["agent_client_prefix"] == "bindu-agent-"

    def test_prepare_auth_hydra_removes_none_values(self):
        """Test that None values are removed from Hydra settings."""
        auth_config = {
            "enabled": True,
            "provider": "hydra",
            "admin_url": "http://localhost:4445",
            "timeout": None,
            "verify_ssl": None,
        }

        result = prepare_auth_settings(auth_config)

        assert result is not None
        assert "timeout" not in result["hydra"]
        assert "verify_ssl" not in result["hydra"]
        assert "admin_url" in result["hydra"]

    def test_prepare_auth_unknown_provider(self):
        """Test preparing auth with unknown provider."""
        auth_config = {
            "enabled": True,
            "provider": "unknown",
        }

        result = prepare_auth_settings(auth_config)

        assert result is not None
        assert result["auth"]["enabled"] is True
        assert result["auth"]["provider"] == "unknown"
        # Should not have hydra settings
        assert "hydra" not in result

    def test_prepare_auth_default_provider(self):
        """Test that default provider is hydra."""
        auth_config = {
            "enabled": True,
        }

        result = prepare_auth_settings(auth_config)

        assert result is not None
        assert result["auth"]["provider"] == "hydra"


class TestPrepareVaultSettings:
    """Test vault settings preparation."""

    def test_prepare_vault_not_configured(self):
        """Test when vault is not configured."""
        result = prepare_vault_settings({})

        # Empty dict returns None (not configured)
        assert result is None

    def test_prepare_vault_partial_config(self):
        """Test when vault config has only URL."""
        vault_config = {"url": "http://localhost:8200"}
        result = prepare_vault_settings(vault_config)

        # Should return settings with vault config
        assert result is not None
        assert "vault" in result
        assert result["vault"]["url"] == "http://localhost:8200"

    def test_prepare_vault_basic(self):
        """Test preparing basic vault settings."""
        vault_config = {
            "enabled": True,
            "url": "http://localhost:8200",
            "token": "vault-token-123",
        }

        result = prepare_vault_settings(vault_config)

        assert result is not None
        assert result["vault"]["enabled"] is True
        assert result["vault"]["url"] == "http://localhost:8200"
        assert result["vault"]["token"] == "vault-token-123"

    def test_prepare_vault_removes_none_values(self):
        """Test that None values are removed from vault settings."""
        vault_config = {
            "enabled": True,
            "url": "http://localhost:8200",
            "token": None,
        }

        result = prepare_vault_settings(vault_config)

        assert result is not None
        assert "token" not in result["vault"]
        assert "url" in result["vault"]

    def test_prepare_vault_disabled(self):
        """Test preparing vault settings when disabled."""
        vault_config = {
            "enabled": False,
            "url": "http://localhost:8200",
        }

        result = prepare_vault_settings(vault_config)

        assert result is not None
        assert result["vault"]["enabled"] is False


class TestUpdateAuthSettings:
    """Test backward-compatible auth settings update."""

    @patch("bindu.settings.app_settings")
    def test_update_auth_settings_hydra(self, mock_app_settings):
        """Test updating auth settings with Hydra provider."""
        auth_config = {
            "enabled": True,
            "provider": "hydra",
            "admin_url": "http://localhost:4445",
            "public_url": "http://localhost:4444",
        }

        update_auth_settings(auth_config)

        # Verify auth settings were updated
        assert mock_app_settings.auth.enabled is True
        assert mock_app_settings.auth.provider == "hydra"

        # Verify hydra settings were updated
        assert mock_app_settings.hydra.admin_url == "http://localhost:4445"
        assert mock_app_settings.hydra.public_url == "http://localhost:4444"

    @patch("bindu.settings.app_settings")
    def test_update_auth_settings_disabled(self, mock_app_settings):
        """Test that disabled auth doesn't update settings."""
        auth_config = {"enabled": False}

        update_auth_settings(auth_config)

        # Should not have called setattr since auth is disabled
        # (prepare_auth_settings returns None)

    @patch("bindu.settings.app_settings")
    def test_update_auth_settings_none(self, mock_app_settings):
        """Test that None config doesn't update settings."""
        update_auth_settings({})

        # Should not raise error


class TestUpdateVaultSettings:
    """Test backward-compatible vault settings update."""

    @patch("bindu.settings.app_settings")
    def test_update_vault_settings(self, mock_app_settings):
        """Test updating vault settings."""
        vault_config = {
            "enabled": True,
            "url": "http://localhost:8200",
            "token": "vault-token",
        }

        update_vault_settings(vault_config)

        # Verify vault settings were updated
        assert mock_app_settings.vault.enabled is True
        assert mock_app_settings.vault.url == "http://localhost:8200"
        assert mock_app_settings.vault.token == "vault-token"

    @patch("bindu.settings.app_settings")
    def test_update_vault_settings_none(self, mock_app_settings):
        """Test that None config doesn't update settings."""
        update_vault_settings({})

        # Should not raise error
