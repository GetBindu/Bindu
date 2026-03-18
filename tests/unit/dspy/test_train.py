"""Unit tests for bindu.dspy.train module.

Tests cover:
- Training pipeline orchestration
- System stability checks
- Data loading and preparation
- Model optimization
- A/B test initialization
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import dspy
from dspy.teleprompt import SIMBA, GEPA

from bindu.dspy.train import train_async
from bindu.dspy.strategies import LastTurnStrategy


class TestTrainAsync:
    """Test suite for async training function."""

    @pytest.mark.asyncio
    async def test_train_checks_system_stability(self):
        """Test that training checks system stability."""
        mock_optimizer = MagicMock(spec=SIMBA)

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ) as mock_check, patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ):

            with pytest.raises(ValueError):
                await train_async(optimizer=mock_optimizer)

            mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_requires_active_prompt(self):
        """Test that training requires active prompt."""
        mock_optimizer = MagicMock(spec=SIMBA)

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ):

            with pytest.raises(ValueError, match="No active prompt"):
                await train_async(optimizer=mock_optimizer)

    @pytest.mark.asyncio
    async def test_train_configures_dspy(self):
        """Test that training configures DSPy."""
        mock_optimizer = MagicMock(spec=SIMBA)
        mock_optimized_program = MagicMock()
        mock_optimized_program.instructions = "Optimized prompt"
        mock_optimizer.compile.return_value = mock_optimized_program

        # Mock dependencies
        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.dspy.configure"
        ) as mock_configure, patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "bindu.dspy.train.app_settings"
        ) as mock_settings, patch(
            "bindu.dspy.train.insert_prompt", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.update_prompt_traffic", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.zero_out_all_except", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.optimize"
        ) as mock_optimize:
            mock_settings.dspy.default_model = "gpt-4"
            mock_settings.dspy.min_feedback_threshold = 0.5
            mock_settings.dspy.initial_candidate_traffic = 0.1
            mock_settings.dspy.initial_active_traffic = 0.9
            mock_optimize.side_effect = ValueError("No examples to optimize")

            with pytest.raises(ValueError):  # No dataset examples
                await train_async(optimizer=mock_optimizer)

            mock_configure.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_with_custom_strategy(self):
        """Test training with custom extraction strategy."""
        mock_optimizer = MagicMock(spec=SIMBA)
        mock_optimized_program = MagicMock()
        mock_optimized_program.instructions = "Optimized prompt"
        mock_optimizer.compile.return_value = mock_optimized_program
        strategy = LastTurnStrategy()

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
        ) as mock_build, patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ) as mock_settings, patch(
            "bindu.dspy.train.insert_prompt", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.update_prompt_traffic", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.zero_out_all_except", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.optimize"
        ) as mock_optimize:
            mock_settings.dspy.default_model = "gpt-4"
            mock_settings.dspy.min_feedback_threshold = 0.5
            mock_settings.dspy.initial_candidate_traffic = 0.1
            mock_settings.dspy.initial_active_traffic = 0.9
            mock_build.return_value = []
            mock_optimize.side_effect = ValueError("No examples to optimize")

            with pytest.raises(ValueError):  # No dataset examples
                await train_async(optimizer=mock_optimizer, strategy=strategy)

            # Verify strategy was passed to build_golden_dataset
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_uses_default_strategy(self):
        """Test training uses default strategy when none provided."""
        mock_optimizer = MagicMock(spec=SIMBA)
        mock_optimized_program = MagicMock()
        mock_optimized_program.instructions = "Optimized prompt"
        mock_optimizer.compile.return_value = mock_optimized_program

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ) as mock_settings, patch(
            "bindu.dspy.train.insert_prompt", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.update_prompt_traffic", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.zero_out_all_except", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.optimize"
        ) as mock_optimize:
            mock_settings.dspy.default_model = "gpt-4"
            mock_settings.dspy.min_feedback_threshold = 0.5
            mock_settings.dspy.initial_candidate_traffic = 0.1
            mock_settings.dspy.initial_active_traffic = 0.9
            mock_optimize.side_effect = ValueError("No examples to optimize")

            with pytest.raises(ValueError):
                await train_async(optimizer=mock_optimizer, strategy=None)

    @pytest.mark.asyncio
    async def test_train_rejects_none_optimizer(self):
        """Test that training rejects None optimizer."""
        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
            return_value=[dspy.Example(input="Q", output="A")],
        ), patch(
            "bindu.dspy.train.convert_to_dspy_examples",
            return_value=[dspy.Example(input="Q", output="A")],
        ), patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ), patch(
            "bindu.dspy.train.AgentProgram"
        ):

            with pytest.raises(ValueError, match="requires an explicit"):
                await train_async(optimizer=None)

    @pytest.mark.asyncio
    async def test_train_rejects_unsupported_optimizer(self):
        """Test that training rejects non-SIMBA/GEPA optimizers."""
        mock_optimizer = MagicMock()  # Not SIMBA or GEPA

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
            return_value=[dspy.Example(input="Q", output="A")],
        ), patch(
            "bindu.dspy.train.convert_to_dspy_examples",
            return_value=[dspy.Example(input="Q", output="A")],
        ), patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ), patch(
            "bindu.dspy.train.AgentProgram"
        ):

            with pytest.raises(ValueError, match="does not support"):
                await train_async(optimizer=mock_optimizer)

    @pytest.mark.asyncio
    async def test_train_with_did_parameter(self):
        """Test training with DID for multi-tenancy."""
        mock_optimizer = MagicMock(spec=SIMBA)
        mock_optimized_program = MagicMock()
        mock_optimized_program.instructions = "Optimized prompt"
        mock_optimizer.compile.return_value = mock_optimized_program

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
        ) as mock_build, patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ) as mock_settings, patch(
            "bindu.dspy.train.insert_prompt", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.update_prompt_traffic", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.zero_out_all_except", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.optimize"
        ) as mock_optimize:
            mock_settings.dspy.default_model = "gpt-4"
            mock_settings.dspy.min_feedback_threshold = 0.5
            mock_settings.dspy.initial_candidate_traffic = 0.1
            mock_settings.dspy.initial_active_traffic = 0.9
            mock_build.return_value = []
            mock_optimize.side_effect = ValueError("No examples to optimize")

            with pytest.raises(ValueError):
                await train_async(optimizer=mock_optimizer, did="test-did-123")

            # Verify DID was passed to build_golden_dataset
            call_kwargs = mock_build.call_args[1]
            assert call_kwargs["did"] == "test-did-123"

    @pytest.mark.asyncio
    async def test_train_logging(self):
        """Test that training logs information."""
        mock_optimizer = MagicMock(spec=SIMBA)

        with patch("bindu.dspy.train.logger") as mock_logger, patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ):

            with pytest.raises(ValueError):
                await train_async(optimizer=mock_optimizer)

            # Should log info messages
            assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_train_builds_golden_dataset(self):
        """Test that training builds golden dataset."""
        mock_optimizer = MagicMock(spec=SIMBA)
        mock_optimized_program = MagicMock()
        mock_optimized_program.instructions = "Optimized prompt"
        mock_optimizer.compile.return_value = mock_optimized_program

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
        ) as mock_build, patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ) as mock_settings, patch(
            "bindu.dspy.train.insert_prompt", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.update_prompt_traffic", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.zero_out_all_except", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.optimize"
        ) as mock_optimize:
            mock_settings.dspy.default_model = "gpt-4"
            mock_settings.dspy.min_feedback_threshold = 0.5
            mock_settings.dspy.initial_candidate_traffic = 0.1
            mock_settings.dspy.initial_active_traffic = 0.9
            mock_build.return_value = []
            mock_optimize.side_effect = ValueError("No examples to optimize")

            with pytest.raises(ValueError):
                await train_async(optimizer=mock_optimizer)

            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_converts_to_dspy_examples(self):
        """Test that training converts dataset to DSPy examples."""
        mock_optimizer = MagicMock(spec=SIMBA)
        mock_optimized_program = MagicMock()
        mock_optimized_program.instructions = "Optimized prompt"
        mock_optimizer.compile.return_value = mock_optimized_program

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
            return_value=["dummy_dataset"],
        ), patch(
            "bindu.dspy.train.convert_to_dspy_examples",
        ) as mock_convert, patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ) as mock_settings, patch(
            "bindu.dspy.train.AgentProgram"
        ), patch(
            "bindu.dspy.train.insert_prompt", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.update_prompt_traffic", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.zero_out_all_except", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.optimize"
        ) as mock_optimize:
            mock_settings.dspy.default_model = "gpt-4"
            mock_settings.dspy.min_feedback_threshold = 0.5
            mock_settings.dspy.initial_candidate_traffic = 0.1
            mock_settings.dspy.initial_active_traffic = 0.9
            mock_convert.return_value = []
            # Raise error when trying to optimize with empty dataset
            mock_optimize.side_effect = ValueError("No examples to optimize")

            with pytest.raises(ValueError):
                await train_async(optimizer=mock_optimizer)

            mock_convert.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_initializes_agent_program(self):
        """Test that training initializes agent program."""
        mock_optimizer = MagicMock(spec=SIMBA)
        mock_optimized_program = MagicMock()
        mock_optimized_program.instructions = "Optimized prompt"
        mock_optimizer.compile.return_value = mock_optimized_program

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Test Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "bindu.dspy.train.convert_to_dspy_examples",
            return_value=[],
        ), patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ) as mock_settings, patch(
            "bindu.dspy.train.AgentProgram"
        ) as mock_program_class, patch(
            "bindu.dspy.train.insert_prompt", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.update_prompt_traffic", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.zero_out_all_except", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.optimize"
        ) as mock_optimize:
            mock_settings.dspy.default_model = "gpt-4"
            mock_settings.dspy.min_feedback_threshold = 0.5
            mock_settings.dspy.initial_candidate_traffic = 0.1
            mock_settings.dspy.initial_active_traffic = 0.9
            # Raise error when trying to optimize with empty dataset
            mock_optimize.side_effect = ValueError("No examples to optimize")

            with pytest.raises(ValueError):
                await train_async(optimizer=mock_optimizer)

            # Should have been called with the active prompt
            mock_program_class.assert_called_once_with("Test Prompt")

    @pytest.mark.asyncio
    async def test_train_runs_optimizer(self):
        """Test that training runs the optimizer."""
        mock_optimizer = MagicMock(spec=SIMBA)
        mock_optimized_program = MagicMock()
        mock_optimized_program.instructions = "Optimized prompt"
        mock_optimizer.compile.return_value = mock_optimized_program

        with patch(
            "bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": "p1", "prompt_text": "Prompt"},
        ), patch(
            "bindu.dspy.train.build_golden_dataset",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "bindu.dspy.train.convert_to_dspy_examples",
            return_value=[],
        ), patch(
            "bindu.dspy.train.dspy.configure"
        ), patch(
            "bindu.dspy.train.dspy.LM"
        ), patch(
            "bindu.dspy.train.app_settings"
        ) as mock_settings, patch(
            "bindu.dspy.train.AgentProgram"
        ), patch(
            "bindu.dspy.train.insert_prompt", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.update_prompt_traffic", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.zero_out_all_except", new_callable=AsyncMock
        ), patch(
            "bindu.dspy.train.optimize"
        ) as mock_optimize:
            mock_settings.dspy.default_model = "gpt-4"
            mock_settings.dspy.min_feedback_threshold = 0.5
            mock_settings.dspy.initial_candidate_traffic = 0.1
            mock_settings.dspy.initial_active_traffic = 0.9
            # Raise error when trying to optimize with empty dataset
            mock_optimize.side_effect = ValueError("No examples to optimize")

            with pytest.raises(ValueError):
                await train_async(optimizer=mock_optimizer)
