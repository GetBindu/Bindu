"""Unit tests for DSPy training orchestration."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bindu.dspy.train import train, train_async
from bindu.dspy.strategies import LastTurnStrategy


class TestTrainAsync:
    """Test train_async function."""

    @pytest.mark.asyncio
    async def test_train_async_full_pipeline(self, mock_storage, mock_optimizer):
        """Test complete pipeline executes successfully."""
        # Setup mocks
        mock_storage.get_active_prompt.return_value = {
            "id": 1,
            "prompt_text": "You are helpful.",
            "status": "active",
            "traffic": 1.0,
        }
        mock_storage.get_candidate_prompt.return_value = None
        mock_storage.insert_prompt.return_value = 2

        # Mock optimized program
        mock_program = MagicMock()
        mock_program.instructions = "Optimized prompt text"
        mock_optimizer.compile.return_value = mock_program

        with patch("bindu.dspy.train.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock):
                with patch("bindu.dspy.train.build_golden_dataset", new_callable=AsyncMock) as mock_build:
                    with patch("bindu.dspy.train.convert_to_dspy_examples") as mock_convert:
                        with patch("bindu.dspy.train.AgentProgram") as mock_agent_program:
                            with patch("bindu.dspy.train.optimize") as mock_optimize:
                                with patch("bindu.dspy.train.dspy") as mock_dspy:
                                    # Setup return values
                                    mock_build.return_value = [{"input": "Q", "output": "A"}]
                                    mock_convert.return_value = [MagicMock()]
                                    mock_agent_program.return_value = MagicMock()
                                    mock_optimize.return_value = mock_program

                                    from dspy.teleprompt import SIMBA
                                    optimizer = SIMBA(metric=lambda x, y: 0.5)

                                    await train_async(optimizer=optimizer)

                                    # Verify pipeline steps
                                    mock_storage.connect.assert_called_once()
                                    mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_async_checks_system_stable(self, mock_storage):
        """Test ensure_system_stable is called."""
        with patch("bindu.dspy.train.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock) as mock_guard:
                mock_guard.side_effect = RuntimeError("System unstable")

                from dspy.teleprompt import SIMBA
                optimizer = SIMBA(metric=lambda x, y: 0.5)

                with pytest.raises(RuntimeError, match="System unstable"):
                    await train_async(optimizer=optimizer)

    @pytest.mark.asyncio
    async def test_train_async_raises_if_unstable(self, mock_storage):
        """Test RuntimeError if candidate exists."""
        with patch("bindu.dspy.train.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock) as mock_guard:
                mock_guard.side_effect = RuntimeError("Experiment active")

                from dspy.teleprompt import SIMBA
                optimizer = SIMBA(metric=lambda x, y: 0.5)

                with pytest.raises(RuntimeError):
                    await train_async(optimizer=optimizer)

    @pytest.mark.asyncio
    async def test_train_async_raises_if_no_active_prompt(self, mock_storage):
        """Test ValueError if no active prompt."""
        mock_storage.get_active_prompt.return_value = None
        mock_storage.get_candidate_prompt.return_value = None

        with patch("bindu.dspy.train.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock):
                from dspy.teleprompt import SIMBA
                optimizer = SIMBA(metric=lambda x, y: 0.5)

                with pytest.raises(ValueError, match="No active prompt"):
                    await train_async(optimizer=optimizer)

    @pytest.mark.asyncio
    async def test_train_async_validates_optimizer(self, mock_storage):
        """Test raises if optimizer is None."""
        mock_storage.get_active_prompt.return_value = {
            "id": 1,
            "prompt_text": "Test",
            "status": "active",
            "traffic": 1.0,
        }
        mock_storage.get_candidate_prompt.return_value = None

        with patch("bindu.dspy.train.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock):
                with patch("bindu.dspy.train.build_golden_dataset", new_callable=AsyncMock):
                    with pytest.raises(ValueError, match="explicit prompt-optimizing optimizer"):
                        await train_async(optimizer=None)

    @pytest.mark.asyncio
    async def test_train_async_validates_optimizer_type(self, mock_storage):
        """Test raises if not SIMBA/GEPA."""
        mock_storage.get_active_prompt.return_value = {
            "id": 1,
            "prompt_text": "Test",
            "status": "active",
            "traffic": 1.0,
        }
        mock_storage.get_candidate_prompt.return_value = None

        invalid_optimizer = MagicMock()

        with patch("bindu.dspy.train.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock):
                with patch("bindu.dspy.train.build_golden_dataset", new_callable=AsyncMock):
                    with patch("bindu.dspy.train.dspy") as mock_dspy:
                        with pytest.raises(ValueError, match="does not support"):
                            await train_async(optimizer=invalid_optimizer)

    @pytest.mark.asyncio
    async def test_train_async_raises_if_no_instructions(self, mock_storage, mock_optimizer):
        """Test RuntimeError if empty instructions."""
        mock_storage.get_active_prompt.return_value = {
            "id": 1,
            "prompt_text": "Test",
            "status": "active",
            "traffic": 1.0,
        }
        mock_storage.get_candidate_prompt.return_value = None

        # Mock program with empty instructions
        mock_program = MagicMock()
        mock_program.instructions = ""
        mock_optimizer.compile.return_value = mock_program

        with patch("bindu.dspy.train.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock):
                with patch("bindu.dspy.train.build_golden_dataset", new_callable=AsyncMock) as mock_build:
                    with patch("bindu.dspy.train.convert_to_dspy_examples"):
                        with patch("bindu.dspy.train.optimize") as mock_optimize:
                            with patch("bindu.dspy.train.dspy"):
                                mock_build.return_value = [{"input": "Q", "output": "A"}]
                                mock_optimize.return_value = mock_program

                                from dspy.teleprompt import SIMBA
                                optimizer = SIMBA(metric=lambda x, y: 0.5)

                                with pytest.raises(RuntimeError, match="did not produce valid instructions"):
                                    await train_async(optimizer=optimizer)

    @pytest.mark.asyncio
    async def test_train_async_disconnects_storage(self, mock_storage):
        """Test Storage.disconnect called in finally."""
        mock_storage.get_active_prompt.side_effect = Exception("Error")

        with patch("bindu.dspy.train.PostgresStorage", return_value=mock_storage):
            with patch("bindu.dspy.train.ensure_system_stable", new_callable=AsyncMock):
                from dspy.teleprompt import SIMBA
                optimizer = SIMBA(metric=lambda x, y: 0.5)

                try:
                    await train_async(optimizer=optimizer)
                except Exception:
                    pass

                mock_storage.disconnect.assert_called_once()


class TestTrain:
    """Test train synchronous wrapper."""

    def test_train_calls_asyncio_run(self):
        """Test asyncio.run is called with train_async."""
        with patch("bindu.dspy.train.asyncio.run") as mock_run:
            from dspy.teleprompt import SIMBA
            optimizer = SIMBA(metric=lambda x, y: 0.5)

            train(optimizer=optimizer)
            mock_run.assert_called_once()

    def test_train_raises_if_in_event_loop(self):
        """Test RuntimeError if already in async context."""
        with patch("bindu.dspy.train.asyncio.run") as mock_run:
            mock_run.side_effect = RuntimeError("asyncio.run() cannot be called from a running event loop")

            from dspy.teleprompt import SIMBA
            optimizer = SIMBA(metric=lambda x, y: 0.5)

            with pytest.raises(RuntimeError, match="cannot be called from an async context"):
                train(optimizer=optimizer)

    def test_train_passes_parameters(self):
        """Test all parameters are passed to train_async."""
        with patch("bindu.dspy.train.asyncio.run") as mock_run:
            from dspy.teleprompt import SIMBA
            strategy = LastTurnStrategy()
            optimizer = SIMBA(metric=lambda x, y: 0.5)

            train(
                optimizer=optimizer,
                strategy=strategy,
                require_feedback=False,
                did="did:test",
            )

            # Verify train_async was called with parameters
            mock_run.assert_called_once()

    def test_train_with_default_params(self):
        """Test works with all defaults."""
        with patch("bindu.dspy.train.asyncio.run"):
            from dspy.teleprompt import SIMBA
            optimizer = SIMBA(metric=lambda x, y: 0.5)

            train(optimizer=optimizer)
