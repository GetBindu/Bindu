"""Minimal focused tests for manifest creation."""

import pytest

from bindu.penguin.manifest import validate_agent_function


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
