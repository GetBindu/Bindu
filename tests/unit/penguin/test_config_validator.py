"""Minimal focused tests for ConfigValidator."""

import pytest

from bindu.penguin.config_validator import ConfigValidator


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

        with pytest.raises(ValueError, match="author"):
            ConfigValidator.validate_and_process(config)

    def test_validate_missing_deployment_url_raises(self):
        """Test validation fails when deployment.url is missing."""
        config = {"author": "test@example.com", "name": "TestAgent", "deployment": {}}

        with pytest.raises(ValueError, match="deployment.url"):
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


class TestAgentTrustConfig:
    """Tests for agent_trust config validation (fixes #382)."""

    BASE = {
        "author": "test@example.com",
        "name": "TestAgent",
        "deployment": {"url": "http://localhost:3773"},
    }

    # ------------------------------------------------------------------
    # Valid configurations
    # ------------------------------------------------------------------

    def test_agent_trust_none_is_allowed(self):
        """agent_trust defaults to None and is accepted without errors."""
        result = ConfigValidator.validate_and_process({**self.BASE})
        assert result["agent_trust"] is None

    def test_agent_trust_empty_dict_is_valid(self):
        """An empty dict is a valid (permissive) trust policy."""
        config = {**self.BASE, "agent_trust": {}}
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"] == {}

    def test_agent_trust_valid_full_config(self):
        """A fully-specified valid trust policy passes validation."""
        trust = {
            "required_verification_level": "strict",
            "allowed_origins": ["https://example.com", "*"],
            "max_agent_hierarchy_depth": 3,
        }
        result = ConfigValidator.validate_and_process({**self.BASE, "agent_trust": trust})
        assert result["agent_trust"] == trust

    def test_agent_trust_all_verification_levels(self):
        """Every valid verification level is accepted."""
        for level in ("none", "basic", "standard", "strict"):
            config = {**self.BASE, "agent_trust": {"required_verification_level": level}}
            result = ConfigValidator.validate_and_process(config)
            assert result["agent_trust"]["required_verification_level"] == level

    def test_agent_trust_hierarchy_depth_zero(self):
        """Depth of 0 (no delegation) is valid."""
        config = {**self.BASE, "agent_trust": {"max_agent_hierarchy_depth": 0}}
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["max_agent_hierarchy_depth"] == 0

    # ------------------------------------------------------------------
    # Invalid configurations
    # ------------------------------------------------------------------

    def test_agent_trust_not_dict_raises(self):
        """agent_trust must be a dict, not a string."""
        with pytest.raises(ValueError, match="agent_trust.*dictionary"):
            ConfigValidator.validate_and_process({**self.BASE, "agent_trust": "strict"})

    def test_agent_trust_invalid_verification_level_raises(self):
        """An unrecognised verification level is rejected."""
        with pytest.raises(ValueError, match="required_verification_level"):
            ConfigValidator.validate_and_process(
                {**self.BASE, "agent_trust": {"required_verification_level": "supermax"}}
            )

    def test_agent_trust_verification_level_wrong_type_raises(self):
        """required_verification_level must be a string."""
        with pytest.raises(ValueError, match="required_verification_level.*string"):
            ConfigValidator.validate_and_process(
                {**self.BASE, "agent_trust": {"required_verification_level": 42}}
            )

    def test_agent_trust_allowed_origins_not_list_raises(self):
        """allowed_origins must be a list."""
        with pytest.raises(ValueError, match="allowed_origins.*list"):
            ConfigValidator.validate_and_process(
                {**self.BASE, "agent_trust": {"allowed_origins": "https://example.com"}}
            )

    def test_agent_trust_allowed_origins_non_string_element_raises(self):
        """Each element of allowed_origins must be a string."""
        with pytest.raises(ValueError, match="allowed_origins.*list of strings"):
            ConfigValidator.validate_and_process(
                {**self.BASE, "agent_trust": {"allowed_origins": [123]}}
            )

    def test_agent_trust_hierarchy_depth_negative_raises(self):
        """max_agent_hierarchy_depth must be >= 0."""
        with pytest.raises(ValueError, match="max_agent_hierarchy_depth.*>="):
            ConfigValidator.validate_and_process(
                {**self.BASE, "agent_trust": {"max_agent_hierarchy_depth": -1}}
            )

    def test_agent_trust_hierarchy_depth_wrong_type_raises(self):
        """max_agent_hierarchy_depth must be an integer, not a float."""
        with pytest.raises(ValueError, match="max_agent_hierarchy_depth.*integer"):
            ConfigValidator.validate_and_process(
                {**self.BASE, "agent_trust": {"max_agent_hierarchy_depth": 2.5}}
            )

    def test_agent_trust_hierarchy_depth_bool_rejected(self):
        """bool is a subtype of int in Python; we reject it explicitly."""
        with pytest.raises(ValueError, match="max_agent_hierarchy_depth.*integer"):
            ConfigValidator.validate_and_process(
                {**self.BASE, "agent_trust": {"max_agent_hierarchy_depth": True}}
            )
