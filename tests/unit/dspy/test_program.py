"""Unit tests for bindu.dspy.program module.

Tests cover:
- AgentProgram initialization
- Forward pass execution
- Instructions property access
- Error handling
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from unittest.mock import patch, MagicMock
import dspy

from bindu.dspy.program import AgentProgram


class TestAgentProgram:
    """Test suite for AgentProgram."""

    def test_program_initialization(self):
        """Test AgentProgram initialization."""
        with patch("bindu.dspy.program.dspy.Predict"):
            program = AgentProgram("Be helpful and concise")
            assert program is not None

    def test_program_initializes_predictor(self):
        """Test that program initializes predictor."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict:
            program = AgentProgram("Test prompt")
            mock_predict.assert_called_once()

    def test_program_with_empty_prompt(self):
        """Test program initialization with empty prompt."""
        with patch("bindu.dspy.program.dspy.Predict"):
            program = AgentProgram("")
            assert program is not None

    def test_program_with_multiline_prompt(self):
        """Test program with multiline instructions."""
        prompt = """Be helpful.
        Answer questions accurately.
        Be concise."""

        with patch("bindu.dspy.program.dspy.Predict"):
            program = AgentProgram(prompt)
            assert program is not None

    def test_program_forward_valid_input(self):
        """Test forward pass with valid input."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor

            mock_prediction = MagicMock()
            mock_prediction.output = "Generated response"
            mock_predictor.return_value = mock_prediction

            program = AgentProgram("Be helpful")
            result = program.forward("What is today?")

            assert result is not None
            assert hasattr(result, "output")

    def test_program_forward_predictor_called(self):
        """Test that forward calls the predictor."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor
            mock_prediction = MagicMock()
            mock_prediction.output = "Response"
            mock_predictor.return_value = mock_prediction

            program = AgentProgram("Prompt")
            program.forward("Test input")

            mock_predictor.assert_called_once_with(input="Test input")

    def test_program_forward_none_predictor_result(self):
        """Test forward handles None predictor result."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor
            mock_predictor.return_value = None

            program = AgentProgram("Prompt")
            result = program.forward("Input")

            assert result is None

    def test_program_forward_missing_output_field(self):
        """Test forward handles prediction without output field."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor

            mock_prediction = MagicMock(spec=[])  # No output attribute
            mock_predictor.return_value = mock_prediction

            program = AgentProgram("Prompt")
            result = program.forward("Input")

            assert result is None

    def test_program_forward_exception_handling(self):
        """Test forward handles exceptions."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor
            mock_predictor.side_effect = Exception("Predictor error")

            program = AgentProgram("Prompt")
            result = program.forward("Input")

            assert result is None

    def test_program_instructions_property(self):
        """Test accessing instructions property."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor

            mock_signature = MagicMock()
            mock_signature.instructions = "Original prompt"
            mock_predictor.signature = mock_signature

            program = AgentProgram("Original prompt")
            instructions = program.instructions

            assert instructions == "Original prompt"

    def test_program_is_dspy_module(self):
        """Test that AgentProgram is a dspy.Module."""
        with patch("bindu.dspy.program.dspy.Predict"):
            assert issubclass(AgentProgram, dspy.Module)

    def test_program_forward_empty_input(self):
        """Test forward with empty input string."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor
            mock_prediction = MagicMock()
            mock_prediction.output = "Response"
            mock_predictor.return_value = mock_prediction

            program = AgentProgram("Prompt")
            result = program.forward("")

            assert result is not None

    def test_program_forward_multiline_input(self):
        """Test forward with multiline input."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor
            mock_prediction = MagicMock()
            mock_prediction.output = "Response"
            mock_predictor.return_value = mock_prediction

            program = AgentProgram("Prompt")
            multiline_input = "Line 1\nLine 2\nLine 3"
            result = program.forward(multiline_input)

            assert result is not None
            # Verify input was passed correctly
            mock_predictor.assert_called_once_with(input=multiline_input)

    def test_program_multiple_forwards(self):
        """Test multiple forward passes."""
        with patch("bindu.dspy.program.dspy.Predict") as mock_predict_class:
            mock_predictor = MagicMock()
            mock_predict_class.return_value = mock_predictor
            mock_prediction = MagicMock()
            mock_prediction.output = "Response"
            mock_predictor.return_value = mock_prediction

            program = AgentProgram("Prompt")

            result1 = program.forward("Input 1")
            result2 = program.forward("Input 2")
            result3 = program.forward("Input 3")

            assert result1 is not None
            assert result2 is not None
            assert result3 is not None
            assert mock_predictor.call_count == 3
