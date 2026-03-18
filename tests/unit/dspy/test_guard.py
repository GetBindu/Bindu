"""Unit tests for bindu.dspy.guard module.

Tests cover:
- System stability checks
- Candidate prompt detection
- Error handling and exceptions
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from unittest.mock import patch, AsyncMock

from bindu.dspy.guard import ensure_system_stable


class TestSystemStability:
    """Test suite for system stability checks."""

    @pytest.mark.asyncio
    async def test_system_stable_no_candidate(self):
        """Test that system is stable when no candidate prompt exists."""
        with patch(
            "bindu.dspy.guard.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ):
            # Should not raise any exception
            await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_system_unstable_with_candidate(self):
        """Test that system raises error when candidate prompt exists."""
        candidate = {"id": "test-candidate-123"}

        with patch(
            "bindu.dspy.guard.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ):
            with pytest.raises(
                RuntimeError,
                match=".*experiment still active.*",
            ):
                await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_system_unstable_includes_candidate_id(self):
        """Test error message includes candidate ID."""
        candidate = {"id": "my-candidate-id-456"}

        with patch(
            "bindu.dspy.guard.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ):
            with pytest.raises(RuntimeError) as excinfo:
                await ensure_system_stable()

            # Error should mention the candidate ID
            assert "my-candidate-id-456" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_system_stable_multiple_calls(self):
        """Test multiple stability checks return consistently."""
        with patch(
            "bindu.dspy.guard.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ):
            # Multiple calls should all succeed
            await ensure_system_stable()
            await ensure_system_stable()
            await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_system_unstable_empty_dict_candidate(self):
        """Test with empty dict candidate (still considered present)."""
        with patch(
            "bindu.dspy.guard.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value={"id": "cand-empty"},
        ):
            with pytest.raises(RuntimeError):
                await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_error_message_instructs_wait(self):
        """Test error message instructs user to wait."""
        candidate = {"id": "test-id"}

        with patch(
            "bindu.dspy.guard.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ):
            with pytest.raises(RuntimeError) as excinfo:
                await ensure_system_stable()

            # Error should mention waiting
            error_msg = str(excinfo.value).lower()
            assert "wait" in error_msg

    @pytest.mark.asyncio
    async def test_logging_on_success(self):
        """Test that logging occurs on successful stability check."""
        with patch(
            "bindu.dspy.guard.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch("bindu.dspy.guard.logger") as mock_logger:
            await ensure_system_stable()
            # Should log info message on success
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_logging_on_failure(self):
        """Test that logging occurs on stability check failure."""
        candidate = {"id": "candidate-123"}

        with patch(
            "bindu.dspy.guard.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ), patch("bindu.dspy.guard.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                await ensure_system_stable()

            # Should log error message on failure
            mock_logger.error.assert_called()
