"""Comprehensive tests for env_loader utilities."""

import os
from unittest.mock import patch

from bindu.utils.config.env_loader import (
    create_storage_config_from_env,
    create_scheduler_config_from_env,
    create_tunnel_config_from_env,
    create_sentry_config_from_env,
    create_auth_config_from_env,
    create_vault_config_from_env,
)


class TestStorageConfigFromEnv:
    """Test storage configuration creation."""

    def test_storage_from_user_config_postgres(self):
        """Test creating storage config from user config."""
        user_config = {
            "storage": {
                "type": "postgres",
                "postgres_url": "postgresql://localhost/test",
            }
        }

        result = create_storage_config_from_env(user_config)

        assert result.type == "postgres"
        assert result.database_url == "postgresql://localhost/test"

    def test_storage_from_user_config_memory(self):
        """Test creating memory storage config from user config."""
        user_config = {"storage": {"type": "memory"}}

        result = create_storage_config_from_env(user_config)

        assert result.type == "memory"
        assert result.database_url is None

    def test_storage_invalid_type_defaults_to_memory(self):
        """Test that invalid storage type defaults to memory."""
        user_config = {"storage": {"type": "invalid"}}

        result = create_storage_config_from_env(user_config)

        assert result.type == "memory"

    def test_storage_from_env_memory(self):
        """Test creating storage config from environment."""
        user_config = {}

        with patch.dict(os.environ, {"STORAGE_TYPE": "memory"}):
            result = create_storage_config_from_env(user_config)

        assert result.type == "memory"

    def test_storage_from_env_postgres(self):
        """Test creating postgres storage from environment."""
        user_config = {}

        with patch.dict(
            os.environ,
            {"STORAGE_TYPE": "postgres", "DATABASE_URL": "postgresql://localhost/db"},
        ):
            result = create_storage_config_from_env(user_config)

        assert result.type == "postgres"
        assert result.database_url == "postgresql://localhost/db"

    def test_storage_from_env_invalid_type(self):
        """Test invalid storage type from environment."""
        user_config = {}

        with patch.dict(os.environ, {"STORAGE_TYPE": "invalid"}):
            result = create_storage_config_from_env(user_config)

        assert result.type == "memory"

    def test_storage_not_configured(self):
        """Test when storage is not configured."""
        user_config = {}

        with patch.dict(os.environ, {}, clear=True):
            result = create_storage_config_from_env(user_config)

        assert result is None


class TestSchedulerConfigFromEnv:
    """Test scheduler configuration creation."""

    def test_scheduler_from_user_config_redis(self):
        """Test creating redis scheduler from user config."""
        user_config = {
            "scheduler": {"type": "redis", "redis_url": "redis://localhost:6379"}
        }

        result = create_scheduler_config_from_env(user_config)

        assert result.type == "redis"
        assert result.redis_url == "redis://localhost:6379"

    def test_scheduler_from_user_config_memory(self):
        """Test creating memory scheduler from user config."""
        user_config = {"scheduler": {"type": "memory"}}

        result = create_scheduler_config_from_env(user_config)

        assert result.type == "memory"
        assert result.redis_url is None

    def test_scheduler_invalid_type_defaults_to_memory(self):
        """Test that invalid scheduler type defaults to memory."""
        user_config = {"scheduler": {"type": "invalid"}}

        result = create_scheduler_config_from_env(user_config)

        assert result.type == "memory"

    def test_scheduler_from_env_memory(self):
        """Test creating scheduler from environment."""
        user_config = {}

        with patch.dict(os.environ, {"SCHEDULER_TYPE": "memory"}):
            result = create_scheduler_config_from_env(user_config)

        assert result.type == "memory"

    def test_scheduler_from_env_redis(self):
        """Test creating redis scheduler from environment."""
        user_config = {}

        with patch.dict(
            os.environ,
            {"SCHEDULER_TYPE": "redis", "REDIS_URL": "redis://localhost:6379"},
        ):
            result = create_scheduler_config_from_env(user_config)

        assert result.type == "redis"
        assert result.redis_url == "redis://localhost:6379"

    def test_scheduler_from_env_invalid_type(self):
        """Test invalid scheduler type from environment."""
        user_config = {}

        with patch.dict(os.environ, {"SCHEDULER_TYPE": "invalid"}):
            result = create_scheduler_config_from_env(user_config)

        assert result.type == "memory"

    def test_scheduler_not_configured(self):
        """Test when scheduler is not configured."""
        user_config = {}

        with patch.dict(os.environ, {}, clear=True):
            result = create_scheduler_config_from_env(user_config)

        assert result is None


class TestTunnelConfigFromEnv:
    """Test tunnel configuration creation."""

    def test_tunnel_from_user_config(self):
        """Test creating tunnel config from user config."""
        user_config = {
            "tunnel": {
                "enabled": True,
                "server_address": "custom.server:7000",
                "subdomain": "my-agent",
                "tunnel_domain": "custom.tunnel.com",
                "protocol": "https",
                "use_tls": True,
                "local_host": "0.0.0.0",
            }
        }

        result = create_tunnel_config_from_env(user_config)

        assert result.enabled is True
        assert result.server_address == "custom.server:7000"
        assert result.subdomain == "my-agent"
        assert result.tunnel_domain == "custom.tunnel.com"
        assert result.protocol == "https"
        assert result.use_tls is True
        assert result.local_host == "0.0.0.0"

    def test_tunnel_from_user_config_with_defaults(self):
        """Test tunnel config with default values."""
        user_config = {"tunnel": {"enabled": True}}

        result = create_tunnel_config_from_env(user_config)

        assert result.enabled is True
        assert result.server_address == "142.132.241.44:7000"
        assert result.tunnel_domain == "tunnel.getbindu.com"
        assert result.protocol == "http"
        assert result.use_tls is False
        assert result.local_host == "127.0.0.1"

    def test_tunnel_from_env_enabled(self):
        """Test creating tunnel from environment."""
        user_config = {}

        env_vars = {
            "TUNNEL_ENABLED": "true",
            "TUNNEL_SERVER_ADDRESS": "server:7000",
            "TUNNEL_SUBDOMAIN": "test-agent",
            "TUNNEL_DOMAIN": "test.tunnel.com",
            "TUNNEL_PROTOCOL": "https",
            "TUNNEL_USE_TLS": "true",
            "TUNNEL_LOCAL_HOST": "0.0.0.0",
        }

        with patch.dict(os.environ, env_vars):
            result = create_tunnel_config_from_env(user_config)

        assert result.enabled is True
        assert result.server_address == "server:7000"
        assert result.subdomain == "test-agent"
        assert result.tunnel_domain == "test.tunnel.com"
        assert result.protocol == "https"
        assert result.use_tls is True
        assert result.local_host == "0.0.0.0"

    def test_tunnel_disabled(self):
        """Test when tunnel is disabled."""
        user_config = {}

        with patch.dict(os.environ, {"TUNNEL_ENABLED": "false"}):
            result = create_tunnel_config_from_env(user_config)

        assert result is None

    def test_tunnel_not_configured(self):
        """Test when tunnel is not configured."""
        user_config = {}

        with patch.dict(os.environ, {}, clear=True):
            result = create_tunnel_config_from_env(user_config)

        assert result is None


class TestSentryConfigFromEnv:
    """Test Sentry configuration creation."""

    def test_sentry_from_user_config(self):
        """Test creating Sentry config from user config."""
        user_config = {
            "sentry": {
                "enabled": True,
                "dsn": "https://example.com/sentry",
                "environment": "production",
                "release": "1.0.0",
                "traces_sample_rate": 0.5,
                "profiles_sample_rate": 0.2,
                "enable_tracing": False,
                "send_default_pii": True,
                "debug": True,
            }
        }

        result = create_sentry_config_from_env(user_config)

        assert result.enabled is True
        assert result.dsn == "https://example.com/sentry"
        assert result.environment == "production"
        assert result.release == "1.0.0"
        assert result.traces_sample_rate == 0.5
        assert result.profiles_sample_rate == 0.2
        assert result.enable_tracing is False
        assert result.send_default_pii is True
        assert result.debug is True

    def test_sentry_disabled_in_user_config(self):
        """Test when Sentry is disabled in user config."""
        user_config = {"sentry": {"enabled": False}}

        result = create_sentry_config_from_env(user_config)

        assert result is None

    def test_sentry_from_env(self):
        """Test creating Sentry from environment."""
        user_config = {}

        with patch.dict(
            os.environ, {"SENTRY_ENABLED": "true", "SENTRY_DSN": "https://example.com"}
        ):
            result = create_sentry_config_from_env(user_config)

        assert result.enabled is True
        assert result.dsn == "https://example.com"

    def test_sentry_disabled_from_env(self):
        """Test when Sentry is disabled from environment."""
        user_config = {}

        with patch.dict(os.environ, {"SENTRY_ENABLED": "false"}):
            result = create_sentry_config_from_env(user_config)

        assert result is None

    def test_sentry_not_configured(self):
        """Test when Sentry is not configured."""
        user_config = {}

        with patch.dict(os.environ, {}, clear=True):
            result = create_sentry_config_from_env(user_config)

        assert result is None


class TestAuthConfigFromEnv:
    """Test auth configuration extraction."""

    def test_auth_config_extraction(self):
        """Test extracting auth config from validated config."""
        user_config = {
            "auth": {
                "enabled": True,
                "provider": "hydra",
                "admin_url": "http://localhost:4445",
            }
        }

        result = create_auth_config_from_env(user_config)

        assert result == user_config["auth"]

    def test_auth_config_not_present(self):
        """Test when auth config is not present."""
        user_config = {}

        result = create_auth_config_from_env(user_config)

        assert result is None


class TestVaultConfigFromEnv:
    """Test vault configuration extraction."""

    def test_vault_config_extraction(self):
        """Test extracting vault config from validated config."""
        user_config = {
            "vault": {
                "enabled": True,
                "url": "http://localhost:8200",
                "token": "vault-token",
            }
        }

        result = create_vault_config_from_env(user_config)

        assert result == user_config["vault"]

    def test_vault_config_not_present(self):
        """Test when vault config is not present."""
        user_config = {}

        result = create_vault_config_from_env(user_config)

        assert result is None
