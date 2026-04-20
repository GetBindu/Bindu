"""Minimal focused tests for ConfigValidator."""

import pytest

from bindu.penguin.config_validator import ConfigError, ConfigValidator


class TestConfigValidator:
    """Test ConfigValidator with strong test cases."""

    def test_validate_and_process_valid_config(self):
        """Test validation and processing of valid config."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "http://localhost:3773"},
        }

        result = ConfigValidator.validate_and_process(config)

        assert result is not None
        assert result["name"] == "TestAgent"
        assert result["author"] == "test@example.com"

    def test_validate_missing_required_field_raises(self):
        """Test validation fails when required field is missing."""
        config = {"version": "1.0.0"}

        with pytest.raises(ConfigError, match="author"):
            ConfigValidator.validate_and_process(config)

    def test_validate_missing_deployment_url_raises(self):
        """Test validation fails when deployment.url is missing."""
        config = {"author": "test@example.com", "name": "TestAgent", "deployment": {}}

        with pytest.raises(ConfigError, match="deployment.url"):
            ConfigValidator.validate_and_process(config)

    def test_validate_invalid_deployment_url_scheme_raises(self):
        """Test validation fails when deployment.url has invalid scheme."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "ftp://localhost:3773"},
        }

        with pytest.raises(ConfigError, match="valid http\(s\) URL"):
            ConfigValidator.validate_and_process(config)

    def test_validate_invalid_deployment_url_format_raises(self):
        """Test validation fails when deployment.url is not a valid URL."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "localhost:3773"},
        }

        with pytest.raises(ConfigError, match="deployment.url"):
            ConfigValidator.validate_and_process(config)

    def test_defaults_are_applied(self):
        """Test that default values are applied to config."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "http://localhost:3773"},
        }

        result = ConfigValidator.validate_and_process(config)

        assert result["kind"] == "agent"
        assert result["num_history_sessions"] == 10
        assert result["debug_mode"] is False
