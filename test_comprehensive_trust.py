"""Tests for configuration validation and processing."""

import pytest

from bindu.penguin.config_validator import ConfigValidator


class TestConfigValidatorBasics:
    """Test basic configuration validation."""

    def test_validate_required_fields_missing(self):
        """Test that missing required fields raise ValueError."""
        config = {"name": "test-agent"}
        with pytest.raises(ValueError, match="Missing required fields"):
            ConfigValidator.validate_and_process(config)

    def test_validate_required_fields_present(self):
        """Test that validation passes with required fields."""
        config = {"author": "test@example.com", "deployment": {}}
        result = ConfigValidator.validate_and_process(config)
        assert result["author"] == "test@example.com"
        assert result["deployment"] == {}

    def test_defaults_applied(self):
        """Test that default values are applied."""
        config = {"author": "test@example.com", "deployment": {}}
        result = ConfigValidator.validate_and_process(config)
        assert result["name"] == "bindu-agent"
        assert result["debug_mode"] is False
        assert result["telemetry"] is True
        assert result["recreate_keys"] is False

    def test_custom_values_override_defaults(self):
        """Test that custom values override defaults."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "name": "custom-agent",
            "debug_mode": True,
        }
        result = ConfigValidator.validate_and_process(config)
        assert result["name"] == "custom-agent"
        assert result["debug_mode"] is True


class TestAgentTrustValidation:
    """Test agent trust configuration validation."""

    def test_agent_trust_valid_config(self):
        """Test valid agent trust configuration."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "allowed_origins": ["https://example.com"],
            },
        }
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["required_verification_level"] == "admin"
        assert result["agent_trust"]["max_agent_hierarchy_depth"] == 5

    def test_agent_trust_missing_required_fields(self):
        """Test that missing required fields in agent_trust raise ValueError."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {"identity_provider": "hydra"},  # Missing required fields
        }
        with pytest.raises(ValueError, match="Invalid agent_trust configuration"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_invalid_verification_level(self):
        """Test invalid verification level."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "invalid_level",
                "max_agent_hierarchy_depth": 5,
            },
        }
        with pytest.raises(
            ValueError, match="Invalid required_verification_level"
        ):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_valid_verification_levels(self):
        """Test all valid verification levels."""
        valid_levels = [
            "admin",
            "analyst",
            "auditor",
            "editor",
            "guest",
            "manager",
            "operator",
            "super_admin",
            "support",
            "viewer",
        ]
        for level in valid_levels:
            config = {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": {
                    "required_verification_level": level,
                    "max_agent_hierarchy_depth": 5,
                },
            }
            result = ConfigValidator.validate_and_process(config)
            assert result["agent_trust"]["required_verification_level"] == level

    def test_agent_trust_invalid_hierarchy_depth(self):
        """Test invalid agent hierarchy depth."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 0,  # Invalid: must be >= 1
            },
        }
        with pytest.raises(
            ValueError, match="Invalid max_agent_hierarchy_depth"
        ):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_valid_hierarchy_depths(self):
        """Test valid hierarchy depths."""
        for depth in [1, 2, 5, 10, 100]:
            config = {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": {
                    "required_verification_level": "admin",
                    "max_agent_hierarchy_depth": depth,
                },
            }
            result = ConfigValidator.validate_and_process(config)
            assert result["agent_trust"]["max_agent_hierarchy_depth"] == depth

    def test_agent_trust_invalid_allowed_origins(self):
        """Test invalid allowed origins."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "allowed_origins": "https://example.com",  # Should be list
            },
        }
        with pytest.raises(ValueError, match="allowed_origins"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_valid_allowed_origins(self):
        """Test valid allowed origins."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "allowed_origins": [
                    "https://example.com",
                    "https://api.example.com",
                    "https://*.example.com",
                ],
            },
        }
        result = ConfigValidator.validate_and_process(config)
        assert len(result["agent_trust"]["allowed_origins"]) == 3

    def test_agent_trust_invalid_origin_format(self):
        """Test invalid origin format."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "allowed_origins": ["invalid-origin"],  # Missing http:// or https://
            },
        }
        with pytest.raises(ValueError, match="Invalid origin format"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_invalid_identity_provider(self):
        """Test invalid identity provider."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "identity_provider": "invalid_provider",
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
            },
        }
        with pytest.raises(ValueError, match="Invalid identity_provider"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_valid_identity_provider(self):
        """Test valid identity provider."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "identity_provider": "hydra",
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
            },
        }
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["identity_provider"] == "hydra"

    def test_agent_trust_boolean_fields(self):
        """Test boolean fields in trust config."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "trust_verification_required": True,
                "certificate_required": False,
            },
        }
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["trust_verification_required"] is True
        assert result["agent_trust"]["certificate_required"] is False

    def test_agent_trust_invalid_boolean_fields(self):
        """Test invalid boolean fields in trust config."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "trust_verification_required": "yes",  # Should be boolean
            },
        }
        with pytest.raises(ValueError, match="trust_verification_required"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_metadata(self):
        """Test metadata field in trust config."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "metadata": {"custom_key": "custom_value"},
            },
        }
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["metadata"]["custom_key"] == "custom_value"

    def test_agent_trust_null_allowed(self):
        """Test that agent_trust can be null."""
        config = {"author": "test@example.com", "deployment": {}, "agent_trust": None}
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"] is None


class TestFieldTypeValidation:
    """Test field type validation."""

    def test_string_field_validation(self):
        """Test string field validation."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "name": 123,  # Should be string
        }
        with pytest.raises(ValueError, match="Field 'name' must be a string"):
            ConfigValidator.validate_and_process(config)

    def test_boolean_field_validation(self):
        """Test boolean field validation."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "debug_mode": "true",  # Should be boolean
        }
        with pytest.raises(ValueError, match="Field 'debug_mode' must be a boolean"):
            ConfigValidator.validate_and_process(config)

    def test_debug_level_validation(self):
        """Test debug_level validation."""
        # Valid values
        for level in [1, 2]:
            config = {
                "author": "test@example.com",
                "deployment": {},
                "debug_level": level,
            }
            result = ConfigValidator.validate_and_process(config)
            assert result["debug_level"] == level

        # Invalid values
        for level in [0, 3, "1"]:
            config = {
                "author": "test@example.com",
                "deployment": {},
                "debug_level": level,
            }
            with pytest.raises(ValueError, match="debug_level"):
                ConfigValidator.validate_and_process(config)

    def test_kind_validation(self):
        """Test kind field validation."""
        for kind in ["agent", "team", "workflow"]:
            config = {
                "author": "test@example.com",
                "deployment": {},
                "kind": kind,
            }
            result = ConfigValidator.validate_and_process(config)
            assert result["kind"] == kind

        config = {
            "author": "test@example.com",
            "deployment": {},
            "kind": "invalid",
        }
        with pytest.raises(ValueError, match="Field 'kind' must be one of"):
            ConfigValidator.validate_and_process(config)

    def test_num_history_sessions_validation(self):
        """Test num_history_sessions validation."""
        # Valid values
        for sessions in [0, 1, 10, 100]:
            config = {
                "author": "test@example.com",
                "deployment": {},
                "num_history_sessions": sessions,
            }
            result = ConfigValidator.validate_and_process(config)
            assert result["num_history_sessions"] == sessions

        # Invalid values
        for sessions in [-1, "10"]:
            config = {
                "author": "test@example.com",
                "deployment": {},
                "num_history_sessions": sessions,
            }
            with pytest.raises(ValueError, match="num_history_sessions"):
                ConfigValidator.validate_and_process(config)


class TestComplexFieldProcessing:
    """Test processing of complex fields."""

    def test_process_skills_from_dict_list(self):
        """Test processing skills from dictionary list."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "skills": [
                {
                    "id": "skill1",
                    "name": "Skill 1",
                    "description": "Test skill",
                    "tags": ["test"],
                    "input_modes": ["text/plain"],
                    "output_modes": ["text/plain"],
                }
            ],
        }
        result = ConfigValidator.validate_and_process(config)
        assert len(result["skills"]) == 1
        assert result["skills"][0]["name"] == "Skill 1"

    def test_process_capabilities(self):
        """Test processing capabilities."""
        config = {
            "author": "test@example.com",
            "deployment": {},
            "capabilities": {"push_notifications": True, "streaming": True},
        }
        result = ConfigValidator.validate_and_process(config)
        assert result["capabilities"]["push_notifications"] is True
        assert result["capabilities"]["streaming"] is True


class TestCreateBindufyConfig:
    """Test create_bindufy_config convenience method."""

    def test_create_bindufy_config_success(self):
        """Test successful creation of bindufy config."""
        config = {"author": "test@example.com", "deployment": {}}
        result = ConfigValidator.create_bindufy_config(config)
        assert result["author"] == "test@example.com"
        assert result["deployment"] == {}
        assert result["storage"] == {}
        assert result["scheduler"] == {}

    def test_create_bindufy_config_missing_required(self):
        """Test that missing required fields raise error."""
        config = {"name": "test"}
        with pytest.raises(ValueError):
            ConfigValidator.create_bindufy_config(config)


class TestIntegration:
    """Integration tests for ConfigValidator."""

    def test_invalid_agent_trust_fails_pipeline(self):
        """Test that invalid agent_trust config fails through the full pipeline."""
        config = {
            "author": "test@example.com",
            "deployment": {"url": "http://localhost"},
            "agent_trust": {
                "required_verification_level": "invalid_level",  # Invalid trust level
                "max_agent_hierarchy_depth": 5,
            }
        }

        with pytest.raises(ValueError, match="Invalid required_verification_level"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_none_allowed(self):
        """Test that agent_trust can be None."""
        config = {
            "author": "test@example.com",
            "deployment": {"url": "http://localhost"},
            "agent_trust": None
        }

        # Should pass without error
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"] is None

    def test_agent_trust_invalid_type_fails(self):
        """Test that non-dict agent_trust fails."""
        config = {
            "author": "test@example.com",
            "deployment": {"url": "http://localhost"},
            "agent_trust": "invalid_string"  # Should be dict or None
        }

        with pytest.raises(ValueError, match="Field 'agent_trust' must be a dictionary"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_missing_required_fields_fails(self):
        """Test that missing required fields in agent_trust fail."""
        config = {
            "author": "test@example.com",
            "deployment": {"url": "http://localhost"},
            "agent_trust": {
                "identity_provider": "hydra"
                # Missing required_verification_level and max_agent_hierarchy_depth
            }
        }

        with pytest.raises(ValueError, match="Missing required agent_trust fields"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_missing_one_required_field_fails(self):
        """Test that missing one required field in agent_trust fails."""
        config = {
            "author": "test@example.com",
            "deployment": {"url": "http://localhost"},
            "agent_trust": {
                "required_verification_level": "admin"
                # Missing max_agent_hierarchy_depth
            }
        }

        with pytest.raises(ValueError, match="Missing required agent_trust fields"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_invalid_provider_fails(self):
        """Test that invalid identity provider fails."""
        config = {
            "author": "test@example.com",
            "deployment": {"url": "http://localhost"},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "identity_provider": "invalid_provider"
            }
        }

        with pytest.raises(ValueError, match="Invalid identity_provider"):
            ConfigValidator.validate_and_process(config)

    def test_agent_trust_custom_provider_passes(self):
        """Test that 'custom' identity provider is now supported."""
        config = {
            "author": "test@example.com",
            "deployment": {"url": "http://localhost"},
            "agent_trust": {
                "required_verification_level": "admin",
                "max_agent_hierarchy_depth": 5,
                "identity_provider": "custom"
            }
        }

        # Should pass without error
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["identity_provider"] == "custom"

    def test_full_config_with_agent_trust(self):
        """Test full configuration with agent trust."""
        config = {
            "author": "test@example.com",
            "deployment": {"type": "cloud"},
            "name": "my-agent",
            "description": "My test agent",
            "version": "1.0.0",
            "kind": "agent",
            "debug_mode": True,
            "telemetry": True,
            "agent_trust": {
                "required_verification_level": "manager",
                "max_agent_hierarchy_depth": 3,
                "allowed_origins": [
                    "https://example.com",
                    "https://*.example.com",
                ],
                "trust_verification_required": True,
                "certificate_required": True,
                "metadata": {"custom": "data"},
            },
        }
        result = ConfigValidator.validate_and_process(config)
        assert result["name"] == "my-agent"
        assert result["author"] == "test@example.com"
        assert result["agent_trust"]["required_verification_level"] == "manager"
        assert result["agent_trust"]["max_agent_hierarchy_depth"] == 3

    def test_minimal_config(self):
        """Test minimal configuration."""
        config = {"author": "test@example.com", "deployment": {}}
        result = ConfigValidator.validate_and_process(config)
        # Verify all defaults are present
        assert "name" in result
        assert "version" in result
        assert "debug_mode" in result
