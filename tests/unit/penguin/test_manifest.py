"""Minimal focused tests for manifest creation."""

from unittest.mock import patch

import pytest

from bindu.penguin.manifest import (
    _create_default_agent_trust,
    validate_agent_function,
)


class TestValidateAgentFunction:
    """Test agent function validation."""

    def test_validate_valid_function_success(self):
        """Test validation of valid agent function with messages parameter."""

        def agent_func(messages):
            return "response"

        # Should not raise
        validate_agent_function(agent_func)

    def test_validate_missing_parameter_raises(self):
        """Test validation fails for function without parameters."""

        def agent_func():
            return "response"

        with pytest.raises(ValueError, match="must have at least"):
            validate_agent_function(agent_func)

    def test_validate_wrong_parameter_name_raises(self):
        """Test validation fails for wrong parameter name."""

        def agent_func(message):  # Should be 'messages'
            return "response"

        with pytest.raises(ValueError, match="must be named 'messages'"):
            validate_agent_function(agent_func)

    def test_validate_too_many_parameters_raises(self):
        """Test validation fails for multiple parameters."""

        def agent_func(messages, context):
            return "response"

        with pytest.raises(ValueError, match="must have only"):
            validate_agent_function(agent_func)


class TestDefaultAgentTrustIdentityProvider:
    """The agent-card's advertised identity_provider must match the runtime
    auth provider. A mismatch caused the card to say 'custom' while the
    HydraMiddleware was actually enforcing DID signatures on the wire —
    confusing operators and lying to peers discovering the agent."""

    def test_defaults_to_custom_when_auth_disabled(self):
        with patch("bindu.settings.app_settings") as mock_settings:
            mock_settings.auth.enabled = False
            mock_settings.auth.provider = ""
            trust = _create_default_agent_trust()
        assert trust["identity_provider"] == "custom"

    def test_returns_hydra_when_auth_enabled_and_provider_is_hydra(self):
        with patch("bindu.settings.app_settings") as mock_settings:
            mock_settings.auth.enabled = True
            mock_settings.auth.provider = "hydra"
            trust = _create_default_agent_trust()
        assert trust["identity_provider"] == "hydra"

    def test_returns_hydra_case_insensitive(self):
        """Env var or config may carry 'Hydra' or 'HYDRA' — should still
        match the middleware's case-insensitive comparison."""
        with patch("bindu.settings.app_settings") as mock_settings:
            mock_settings.auth.enabled = True
            mock_settings.auth.provider = "HYDRA"
            trust = _create_default_agent_trust()
        assert trust["identity_provider"] == "hydra"

    def test_returns_custom_when_auth_enabled_but_provider_is_not_hydra(self):
        """Guard the Literal contract — if a future provider lands that
        isn't yet a valid IdentityProvider value, we must fall back to
        'custom' rather than emit a type-invalid card."""
        with patch("bindu.settings.app_settings") as mock_settings:
            mock_settings.auth.enabled = True
            mock_settings.auth.provider = "some-future-provider"
            trust = _create_default_agent_trust()
        assert trust["identity_provider"] == "custom"

    def test_returns_custom_when_auth_enabled_but_provider_missing(self):
        """Defensive — enabled without a provider is a misconfig, but must
        not crash the default trust path."""
        with patch("bindu.settings.app_settings") as mock_settings:
            mock_settings.auth.enabled = True
            # provider attribute missing entirely
            del mock_settings.auth.provider
            mock_settings.auth.provider = None  # re-set as None for getattr
            trust = _create_default_agent_trust()
        assert trust["identity_provider"] == "custom"
