"""Comprehensive tests for config enricher."""

import json
import os
import pytest
from unittest.mock import patch

from bindu.utils.config.enricher import load_config_from_env


class TestDeploymentConfiguration:
    """Test deployment URL/host/port configuration."""

    def test_deployment_url_override(self):
        """Test BINDU_DEPLOYMENT_URL override."""
        config = {"deployment": {"url": "http://localhost:3773"}}

        with patch.dict(
            os.environ, {"BINDU_DEPLOYMENT_URL": "https://example.com:8080"}
        ):
            result = load_config_from_env(config)

        assert result["deployment"]["url"] == "https://example.com:8080"

    def test_deployment_host_override(self):
        """Test BINDU_HOST override."""
        config = {"deployment": {"url": "http://localhost:3773"}}

        with patch.dict(os.environ, {"BINDU_HOST": "example.com"}):
            result = load_config_from_env(config)

        assert "example.com" in result["deployment"]["url"]

    def test_deployment_port_override(self):
        """Test BINDU_PORT override."""
        config = {"deployment": {"url": "http://localhost:3773"}}

        with patch.dict(os.environ, {"BINDU_PORT": "9000"}):
            result = load_config_from_env(config)

        assert ":9000" in result["deployment"]["url"]

    def test_deployment_port_env_fallback(self):
        """Test PORT environment variable fallback."""
        config = {"deployment": {"url": "http://localhost:3773"}}

        with patch.dict(os.environ, {"PORT": "8080"}):
            result = load_config_from_env(config)

        assert ":8080" in result["deployment"]["url"]

    def test_deployment_host_and_port_override(self):
        """Test both host and port override."""
        config = {"deployment": {"url": "http://localhost:3773"}}

        with patch.dict(
            os.environ, {"BINDU_HOST": "example.com", "BINDU_PORT": "9000"}
        ):
            result = load_config_from_env(config)

        assert result["deployment"]["url"] == "http://example.com:9000"

    def test_deployment_invalid_port_raises_error(self):
        """Test that invalid port raises ValueError."""
        config = {"deployment": {"url": "http://localhost:3773"}}

        with patch.dict(os.environ, {"BINDU_PORT": "invalid"}):
            with pytest.raises(ValueError, match="Invalid deployment port"):
                load_config_from_env(config)

    def test_deployment_no_override(self):
        """Test deployment config without environment overrides."""
        config = {"deployment": {"url": "http://localhost:3773"}}

        with patch.dict(os.environ, {}, clear=True):
            result = load_config_from_env(config)

        assert result["deployment"]["url"] == "http://localhost:3773"


class TestStorageConfiguration:
    """Test storage configuration from environment."""

    def test_storage_memory_from_env(self):
        """Test loading memory storage from environment."""
        config = {}

        with patch.dict(os.environ, {"STORAGE_TYPE": "memory"}):
            result = load_config_from_env(config)

        assert result["storage"]["type"] == "memory"

    def test_storage_postgres_from_env(self):
        """Test loading postgres storage from environment."""
        config = {}

        with patch.dict(
            os.environ,
            {"STORAGE_TYPE": "postgres", "DATABASE_URL": "postgresql://localhost/test"},
        ):
            result = load_config_from_env(config)

        assert result["storage"]["type"] == "postgres"
        assert result["storage"]["postgres_url"] == "postgresql://localhost/test"

    def test_storage_postgres_without_url_raises_error(self):
        """Test that postgres without DATABASE_URL raises error."""
        config = {}

        with patch.dict(os.environ, {"STORAGE_TYPE": "postgres"}):
            with pytest.raises(
                ValueError, match="DATABASE_URL environment variable is required"
            ):
                load_config_from_env(config)

    def test_storage_user_config_preserved(self):
        """Test that user-provided storage config is preserved."""
        config = {
            "storage": {"type": "postgres", "postgres_url": "postgresql://user/db"}
        }

        with patch.dict(os.environ, {}, clear=True):
            result = load_config_from_env(config)

        assert result["storage"]["type"] == "postgres"
        assert result["storage"]["postgres_url"] == "postgresql://user/db"


class TestSchedulerConfiguration:
    """Test scheduler configuration from environment."""

    def test_scheduler_memory_from_env(self):
        """Test loading memory scheduler from environment."""
        config = {}

        with patch.dict(os.environ, {"SCHEDULER_TYPE": "memory"}):
            result = load_config_from_env(config)

        assert result["scheduler"]["type"] == "memory"

    def test_scheduler_redis_from_env(self):
        """Test loading redis scheduler from environment."""
        config = {}

        with patch.dict(
            os.environ,
            {"SCHEDULER_TYPE": "redis", "REDIS_URL": "redis://localhost:6379"},
        ):
            result = load_config_from_env(config)

        assert result["scheduler"]["type"] == "redis"
        assert result["scheduler"]["redis_url"] == "redis://localhost:6379"

    def test_scheduler_redis_without_url_raises_error(self):
        """Test that redis without REDIS_URL raises error."""
        config = {}

        with patch.dict(os.environ, {"SCHEDULER_TYPE": "redis"}):
            with pytest.raises(
                ValueError, match="REDIS_URL environment variable is required"
            ):
                load_config_from_env(config)

    def test_scheduler_user_config_preserved(self):
        """Test that user-provided scheduler config is preserved."""
        config = {"scheduler": {"type": "redis", "redis_url": "redis://custom:6379"}}

        with patch.dict(os.environ, {}, clear=True):
            result = load_config_from_env(config)

        assert result["scheduler"]["type"] == "redis"
        assert result["scheduler"]["redis_url"] == "redis://custom:6379"


class TestSentryConfiguration:
    """Test Sentry configuration from environment."""

    def test_sentry_enabled_from_env(self):
        """Test loading Sentry config when enabled."""
        config = {}

        with patch.dict(
            os.environ,
            {"SENTRY_ENABLED": "true", "SENTRY_DSN": "https://example.com/sentry"},
        ):
            result = load_config_from_env(config)

        assert result["sentry"]["enabled"] is True
        assert result["sentry"]["dsn"] == "https://example.com/sentry"

    def test_sentry_enabled_variations(self):
        """Test various ways to enable Sentry."""
        config = {}

        for value in ["true", "1", "yes", "True", "YES"]:
            with patch.dict(
                os.environ,
                {"SENTRY_ENABLED": value, "SENTRY_DSN": "https://example.com"},
            ):
                result = load_config_from_env(config)
                assert result["sentry"]["enabled"] is True

    def test_sentry_disabled_by_default(self):
        """Test that Sentry is not configured when disabled."""
        config = {}

        with patch.dict(os.environ, {"SENTRY_ENABLED": "false"}):
            result = load_config_from_env(config)

        assert "sentry" not in result

    def test_sentry_without_dsn_raises_error(self):
        """Test that enabled Sentry without DSN raises error."""
        config = {}

        with patch.dict(os.environ, {"SENTRY_ENABLED": "true"}):
            with pytest.raises(
                ValueError, match="SENTRY_DSN environment variable is required"
            ):
                load_config_from_env(config)


class TestTelemetryConfiguration:
    """Test telemetry and OLTP configuration."""

    def test_telemetry_enabled_by_default(self):
        """Test that telemetry is enabled by default."""
        config = {}

        with patch.dict(os.environ, {}, clear=True):
            result = load_config_from_env(config)

        assert result["telemetry"] is True

    def test_telemetry_disabled_from_env(self):
        """Test disabling telemetry from environment."""
        config = {}

        with patch.dict(os.environ, {"TELEMETRY_ENABLED": "false"}):
            result = load_config_from_env(config)

        assert result["telemetry"] is False

    def test_oltp_endpoint_from_env(self):
        """Test loading OLTP endpoint when telemetry enabled."""
        config = {}

        with patch.dict(
            os.environ,
            {"TELEMETRY_ENABLED": "true", "OLTP_ENDPOINT": "http://localhost:4318"},
        ):
            result = load_config_from_env(config)

        assert result["oltp_endpoint"] == "http://localhost:4318"

    def test_oltp_service_name_from_env(self):
        """Test loading OLTP service name."""
        config = {}

        with patch.dict(os.environ, {"OLTP_SERVICE_NAME": "my-service"}):
            result = load_config_from_env(config)

        assert result["oltp_service_name"] == "my-service"

    def test_oltp_headers_from_env(self):
        """Test loading OLTP headers as JSON."""
        config = {}
        headers = {"Authorization": "Basic abc123"}

        with patch.dict(os.environ, {"OLTP_HEADERS": json.dumps(headers)}):
            result = load_config_from_env(config)

        assert result["oltp_headers"] == headers

    def test_oltp_headers_invalid_json_raises_error(self):
        """Test that invalid OLTP_HEADERS JSON raises error."""
        config = {}

        with patch.dict(os.environ, {"OLTP_HEADERS": "not-valid-json"}):
            with pytest.raises(ValueError, match="Invalid OLTP_HEADERS format"):
                load_config_from_env(config)

    def test_oltp_not_loaded_when_telemetry_disabled(self):
        """Test that OLTP config is not loaded when telemetry is disabled."""
        config = {}

        with patch.dict(
            os.environ,
            {"TELEMETRY_ENABLED": "false", "OLTP_ENDPOINT": "http://localhost:4318"},
        ):
            result = load_config_from_env(config)

        assert "oltp_endpoint" not in result


class TestPushNotificationsConfiguration:
    """Test push notifications and webhook configuration."""

    def test_webhook_url_from_env(self):
        """Test loading webhook URL when push_notifications enabled."""
        config = {"capabilities": {"push_notifications": True}}

        with patch.dict(os.environ, {"WEBHOOK_URL": "https://example.com/webhook"}):
            result = load_config_from_env(config)

        assert result["global_webhook_url"] == "https://example.com/webhook"

    def test_webhook_token_from_env(self):
        """Test loading webhook token."""
        config = {"capabilities": {"push_notifications": True}}

        with patch.dict(os.environ, {"WEBHOOK_TOKEN": "secret-token"}):
            result = load_config_from_env(config)

        assert result["global_webhook_token"] == "secret-token"

    def test_webhook_not_loaded_without_capability(self):
        """Test that webhook config is not loaded without push_notifications capability."""
        config = {"capabilities": {}}

        with patch.dict(os.environ, {"WEBHOOK_URL": "https://example.com/webhook"}):
            result = load_config_from_env(config)

        assert "global_webhook_url" not in result

    def test_negotiation_api_key_from_env(self):
        """Test loading negotiation API key."""
        config = {"capabilities": {"push_notifications": True, "negotiation": True}}

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "api-key-123"}):
            result = load_config_from_env(config)

        assert result["negotiation"]["embedding_api_key"] == "api-key-123"

    def test_negotiation_preserves_existing_api_key(self):
        """Test that existing API key is not overridden."""
        config = {
            "capabilities": {"push_notifications": True, "negotiation": True},
            "negotiation": {"embedding_api_key": "existing-key"},
        }

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "new-key"}):
            result = load_config_from_env(config)

        assert result["negotiation"]["embedding_api_key"] == "existing-key"


class TestAuthConfiguration:
    """Test authentication configuration."""

    def test_auth_hydra_from_env(self):
        """Test loading Hydra auth configuration."""
        config = {}

        env_vars = {
            "AUTH__ENABLED": "true",
            "AUTH__PROVIDER": "hydra",
            "HYDRA__ADMIN_URL": "http://localhost:4445",
            "HYDRA__PUBLIC_URL": "http://localhost:4444",
        }

        with patch.dict(os.environ, env_vars):
            result = load_config_from_env(config)

        assert result["auth"]["enabled"] is True
        assert result["auth"]["provider"] == "hydra"
        assert result["auth"]["admin_url"] == "http://localhost:4445"
        assert result["auth"]["public_url"] == "http://localhost:4444"

    def test_auth_hydra_connection_settings(self):
        """Test Hydra connection settings."""
        config = {}

        env_vars = {
            "AUTH__ENABLED": "true",
            "AUTH__PROVIDER": "hydra",
            "HYDRA__TIMEOUT": "30",
            "HYDRA__VERIFY_SSL": "false",
            "HYDRA__MAX_RETRIES": "3",
        }

        with patch.dict(os.environ, env_vars):
            result = load_config_from_env(config)

        assert result["auth"]["timeout"] == 30
        assert result["auth"]["verify_ssl"] is False
        assert result["auth"]["max_retries"] == 3

    def test_auth_hydra_cache_settings(self):
        """Test Hydra cache settings."""
        config = {}

        env_vars = {
            "AUTH__ENABLED": "true",
            "AUTH__PROVIDER": "hydra",
            "HYDRA__CACHE_TTL": "300",
            "HYDRA__MAX_CACHE_SIZE": "1000",
        }

        with patch.dict(os.environ, env_vars):
            result = load_config_from_env(config)

        assert result["auth"]["cache_ttl"] == 300
        assert result["auth"]["max_cache_size"] == 1000

    def test_auth_hydra_auto_register_settings(self):
        """Test Hydra auto-registration settings."""
        config = {}

        env_vars = {
            "AUTH__ENABLED": "true",
            "AUTH__PROVIDER": "hydra",
            "HYDRA__AUTO_REGISTER_AGENTS": "false",
            "HYDRA__AGENT_CLIENT_PREFIX": "bindu-agent-",
        }

        with patch.dict(os.environ, env_vars):
            result = load_config_from_env(config)

        assert result["auth"]["auto_register_agents"] is False
        assert result["auth"]["agent_client_prefix"] == "bindu-agent-"

    def test_auth_not_loaded_when_disabled(self):
        """Test that auth is not loaded when disabled."""
        config = {}

        with patch.dict(os.environ, {"AUTH__ENABLED": "false"}):
            result = load_config_from_env(config)

        assert "auth" not in result

    def test_auth_user_config_preserved(self):
        """Test that user-provided auth config is preserved."""
        config = {"auth": {"enabled": True, "provider": "custom"}}

        with patch.dict(os.environ, {}, clear=True):
            result = load_config_from_env(config)

        assert result["auth"]["enabled"] is True
        assert result["auth"]["provider"] == "custom"


class TestVaultConfiguration:
    """Test Vault configuration."""

    def test_vault_from_env(self):
        """Test loading Vault configuration."""
        config = {}

        env_vars = {
            "VAULT__ENABLED": "true",
            "VAULT__URL": "http://localhost:8200",
            "VAULT__TOKEN": "vault-token-123",
        }

        with patch.dict(os.environ, env_vars):
            result = load_config_from_env(config)

        assert result["vault"]["enabled"] is True
        assert result["vault"]["url"] == "http://localhost:8200"
        assert result["vault"]["token"] == "vault-token-123"

    def test_vault_url_fallback(self):
        """Test VAULT_ADDR fallback for URL."""
        config = {}

        with patch.dict(os.environ, {"VAULT_ADDR": "http://vault:8200"}):
            result = load_config_from_env(config)

        assert result["vault"]["url"] == "http://vault:8200"

    def test_vault_token_fallback(self):
        """Test VAULT_TOKEN fallback."""
        config = {}

        with patch.dict(os.environ, {"VAULT_TOKEN": "token-123"}):
            result = load_config_from_env(config)

        assert result["vault"]["token"] == "token-123"

    def test_vault_not_loaded_when_not_configured(self):
        """Test that Vault is not loaded when not configured."""
        config = {}

        with patch.dict(os.environ, {}, clear=True):
            result = load_config_from_env(config)

        assert "vault" not in result


class TestConfigImmutability:
    """Test that input config creates a copy."""

    def test_config_creates_copy(self):
        """Test that a copy is created (note: nested dicts are shallow copied)."""
        original_config = {"capabilities": {"push_notifications": False}}

        with patch.dict(os.environ, {"STORAGE_TYPE": "memory"}):
            result = load_config_from_env(original_config)

        # Result should have new storage config
        assert "storage" in result
        # Original should not have storage
        assert "storage" not in original_config
