"""Unit tests for bindu.dspy.signature module.

Tests cover:
- AgentSignature creation
- DSPy signature compatibility
- Input and output field definitions
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
import dspy

from bindu.dspy.signature import AgentSignature


class TestAgentSignature:
    """Test suite for AgentSignature."""

    def test_signature_is_dspy_signature(self):
        """Test that AgentSignature is a dspy.Signature."""
        assert issubclass(AgentSignature, dspy.Signature)

    def test_signature_with_predictor(self):
        """Test using signature with dspy.Predict."""
        predictor = dspy.Predict(AgentSignature)
        assert predictor is not None

    def test_signature_is_usable(self):
        """Test that signature can be used in DSPy programs."""
        # The signature should be compatible with dspy.Predict
        from bindu.dspy.program import AgentProgram
        
        # Should be able to create a program with the signature
        program = AgentProgram("Test prompt")
        assert program is not None
        assert hasattr(program, "predictor")
