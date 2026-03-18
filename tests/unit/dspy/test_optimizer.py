"""Unit tests for bindu.dspy.optimizer module.

Tests cover:
- Optimizer wrapper functionality
- DSPy optimizer compatibility
- Compilation process
- Error handling
"""

import sys
from unittest.mock import MagicMock, patch

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from unittest.mock import MagicMock
import dspy

from bindu.dspy.optimizer import optimize


class TestOptimizer:
    """Test suite for optimizer wrapper."""

    def test_optimize_with_valid_optimizer(self):
        """Test optimization with valid optimizer."""
        mock_program = MagicMock(spec=dspy.Module)
        mock_dataset = [dspy.Example(input="test", output="expected")]

        mock_optimizer = MagicMock()
        mock_optimized = MagicMock(spec=dspy.Module)
        mock_optimizer.compile.return_value = mock_optimized

        result = optimize(mock_program, mock_dataset, mock_optimizer)

        assert result == mock_optimized
        mock_optimizer.compile.assert_called_once_with(
            mock_program, trainset=mock_dataset
        )

    def test_optimize_calls_compile_method(self):
        """Test that optimize calls compiler.compile()."""
        mock_program = MagicMock()
        mock_dataset = []

        mock_optimizer = MagicMock()
        mock_optimizer.compile.return_value = MagicMock()

        optimize(mock_program, mock_dataset, mock_optimizer)

        mock_optimizer.compile.assert_called_once()

    def test_optimize_passes_program_and_dataset(self):
        """Test that program and dataset are passed to compile."""
        mock_program = MagicMock()
        mock_dataset = [dspy.Example(a="1"), dspy.Example(a="2")]

        mock_optimizer = MagicMock()
        mock_optimizer.compile.return_value = MagicMock()

        optimize(mock_program, mock_dataset, mock_optimizer)

        # Verify the exact arguments
        call_args = mock_optimizer.compile.call_args
        assert call_args[0][0] == mock_program
        assert call_args[1]["trainset"] == mock_dataset

    def test_optimize_returns_optimized_program(self):
        """Test that optimize returns the compiled program."""
        mock_program = MagicMock()
        mock_dataset = []

        mock_optimizer = MagicMock()
        expected_result = MagicMock(spec=dspy.Module)
        mock_optimizer.compile.return_value = expected_result

        result = optimize(mock_program, mock_dataset, mock_optimizer)

        assert result is expected_result

    def test_optimize_raises_without_compile_method(self):
        """Test that TypeError is raised if optimizer has no compile method."""
        mock_program = MagicMock()
        mock_dataset = []

        # Create optimizer without compile method
        mock_optimizer = MagicMock(spec=[])

        with pytest.raises(TypeError, match="does not implement compile"):
            optimize(mock_program, mock_dataset, mock_optimizer)

    def test_optimize_with_empty_dataset(self):
        """Test optimization with empty dataset."""
        mock_program = MagicMock()
        mock_dataset = []

        mock_optimizer = MagicMock()
        mock_optimizer.compile.return_value = MagicMock()

        result = optimize(mock_program, mock_dataset, mock_optimizer)

        assert result is not None
        mock_optimizer.compile.assert_called()

    def test_optimize_with_large_dataset(self):
        """Test optimization with large dataset."""
        mock_program = MagicMock()
        mock_dataset = [
            dspy.Example(input=f"input_{i}", output=f"output_{i}")
            for i in range(1000)
        ]

        mock_optimizer = MagicMock()
        mock_optimizer.compile.return_value = MagicMock()

        result = optimize(mock_program, mock_dataset, mock_optimizer)

        assert result is not None
        # Verify correct size dataset was passed
        call_args = mock_optimizer.compile.call_args
        assert len(call_args[1]["trainset"]) == 1000

    def test_optimize_with_simba_optimizer(self):
        """Test that SIMBA optimizer works with optimize."""
        mock_program = MagicMock()
        mock_dataset = [dspy.Example(input="test", output="output")]

        # Mock SIMBA optimizer
        simba_optimizer = MagicMock()
        mock_compile = MagicMock(return_value=MagicMock(spec=dspy.Module))
        simba_optimizer.compile = mock_compile

        result = optimize(mock_program, mock_dataset, simba_optimizer)

        assert result is not None
        mock_compile.assert_called()

    def test_optimize_preserves_program_type(self):
        """Test that returned program maintains module interface."""
        mock_program = MagicMock(spec=dspy.Module)
        mock_dataset = []

        mock_optimizer = MagicMock()
        expected_result = MagicMock(spec=dspy.Module)
        mock_optimizer.compile.return_value = expected_result

        result = optimize(mock_program, mock_dataset, mock_optimizer)

        # Result should have dspy.Module interface
        assert hasattr(result, "forward") or isinstance(result, dspy.Module)

    def test_optimize_logging(self):
        """Test that optimization logs information."""
        mock_program = MagicMock()
        mock_dataset = [dspy.Example(input="x", output="y")]

        mock_optimizer = MagicMock()
        mock_optimizer.__class__.__name__ = "TestOptimizer"
        mock_optimizer.compile.return_value = MagicMock()

        with patch("bindu.dspy.optimizer.logger") as mock_logger:
            optimize(mock_program, mock_dataset, mock_optimizer)

            # Should log start and completion
            assert mock_logger.info.call_count >= 2

    def test_optimize_error_in_compile(self):
        """Test handling of errors during compile."""
        mock_program = MagicMock()
        mock_dataset = []

        mock_optimizer = MagicMock()
        mock_optimizer.compile.side_effect = RuntimeError("Compile failed")

        with pytest.raises(RuntimeError, match="Compile failed"):
            optimize(mock_program, mock_dataset, mock_optimizer)

    def test_optimize_with_multiple_datasets(self):
        """Test optimization is consistent with multiple calls."""
        mock_program = MagicMock()
        dataset1 = [dspy.Example(input="q1", output="a1")]
        dataset2 = [dspy.Example(input="q2", output="a2")]

        mock_optimizer = MagicMock()
        mock_result1 = MagicMock()
        mock_result2 = MagicMock()
        mock_optimizer.compile.side_effect = [mock_result1, mock_result2]

        result1 = optimize(mock_program, dataset1, mock_optimizer)
        result2 = optimize(mock_program, dataset2, mock_optimizer)

        assert result1 == mock_result1
        assert result2 == mock_result2
        assert mock_optimizer.compile.call_count == 2
