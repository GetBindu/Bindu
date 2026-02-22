"""Unit tests for DSPy prompt management and guards."""

from unittest.mock import AsyncMock, patch

import pytest

from bindu.dspy.prompts import (
    get_active_prompt,
    get_candidate_prompt,
    insert_prompt,
    update_prompt_status,
    update_prompt_traffic,
    zero_out_all_except,
)
from bindu.dspy.guard import ensure_system_stable
from bindu.dspy.prompt_selector import select_prompt_with_canary


class TestGetActivePrompt:
    """Test get_active_prompt function."""

    @pytest.mark.asyncio
    async def test_get_active_prompt_success(self, mock_storage):
        """Test returns prompt dict."""
        mock_storage.get_active_prompt.return_value = {
            "id": 1,
            "prompt_text": "You are helpful.",
            "status": "active",
            "traffic": 1.0,
        }

        with patch("bindu.dspy.prompts.PostgresStorage", return_value=mock_storage):
            result = await get_active_prompt()
            assert result["id"] == 1
            assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_active_prompt_with_storage(self, mock_storage):
        """Test returns prompt dict."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            mock_storage.get_active_prompt.return_value = {"id": 1}
            result = await get_active_prompt()
            assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_active_prompt_creates_storage(self, mock_storage):
        """Test creates storage if None."""
        mock_storage.get_active_prompt.return_value = {"id": 1}

        with patch("bindu.dspy.prompts.PostgresStorage", return_value=mock_storage):
            await get_active_prompt()
            mock_storage.connect.assert_called_once()
            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_prompt_returns_none(self, mock_storage):
        """Test returns None if no active."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            mock_storage.get_active_prompt.return_value = None
            result = await get_active_prompt()
            assert result is None


class TestGetCandidatePrompt:
    """Test get_candidate_prompt function."""

    @pytest.mark.asyncio
    async def test_get_candidate_prompt_success(self, mock_storage):
        """Test returns prompt dict."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            mock_storage.get_candidate_prompt.return_value = {
                "id": 2,
                "prompt_text": "Optimized prompt.",
                "status": "candidate",
                "traffic": 0.1,
            }

            result = await get_candidate_prompt()
            assert result["id"] == 2
            assert result["status"] == "candidate"

    @pytest.mark.asyncio
    async def test_get_candidate_prompt_with_storage(self, mock_storage):
        """Test returns prompt dict."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            mock_storage.get_candidate_prompt.return_value = {"id": 2}
            result = await get_candidate_prompt()
            assert result["id"] == 2

    @pytest.mark.asyncio
    async def test_get_candidate_prompt_returns_none(self, mock_storage):
        """Test returns None if no candidate."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            mock_storage.get_candidate_prompt.return_value = None
            result = await get_candidate_prompt()
            assert result is None


class TestInsertPrompt:
    """Test insert_prompt function."""

    @pytest.mark.asyncio
    async def test_insert_prompt_success(self, mock_storage):
        """Test returns prompt ID."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            mock_storage.insert_prompt.return_value = 5
            result = await insert_prompt(
                text="New prompt",
                status="candidate",
                traffic=0.1,
            )
            assert result == 5

    @pytest.mark.asyncio
    async def test_insert_prompt_calls_storage(self, mock_storage):
        """Test storage.insert_prompt is called."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            mock_storage.insert_prompt.return_value = 1
            await insert_prompt(
                text="Test",
                status="active",
                traffic=1.0,
            )
            mock_storage.insert_prompt.assert_called_once_with("Test", "active", 1.0)

    @pytest.mark.asyncio
    async def test_insert_prompt_with_all_params(self, mock_storage):
        """Test all parameters are passed correctly."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            mock_storage.insert_prompt.return_value = 3

            result = await insert_prompt(
                text="Prompt text",
                status="candidate",
                traffic=0.5,
            )

            assert result == 3


class TestUpdatePromptTraffic:
    """Test update_prompt_traffic function."""

    @pytest.mark.asyncio
    async def test_update_traffic_success(self, mock_storage):
        """Test updates traffic successfully."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            await update_prompt_traffic(1, 0.8)
            mock_storage.update_prompt_traffic.assert_called_once_with(1, 0.8)

    @pytest.mark.asyncio
    async def test_update_traffic_calls_storage(self, mock_storage):
        """Test storage.update_prompt_traffic is called."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            await update_prompt_traffic(5, 0.3)
            mock_storage.update_prompt_traffic.assert_called_with(5, 0.3)


class TestUpdatePromptStatus:
    """Test update_prompt_status function."""

    @pytest.mark.asyncio
    async def test_update_status_success(self, mock_storage):
        """Test updates status successfully."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            await update_prompt_status(1, "deprecated")
            mock_storage.update_prompt_status.assert_called_once_with(1, "deprecated")

    @pytest.mark.asyncio
    async def test_update_status_calls_storage(self, mock_storage):
        """Test storage.update_prompt_status is called."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            await update_prompt_status(3, "rolled_back")
            mock_storage.update_prompt_status.assert_called_with(3, "rolled_back")


class TestZeroOutAllExcept:
    """Test zero_out_all_except function."""

    @pytest.mark.asyncio
    async def test_zero_out_success(self, mock_storage):
        """Test zeros out other prompts."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            await zero_out_all_except([1, 2])
            mock_storage.zero_out_all_except.assert_called_once_with([1, 2])

    @pytest.mark.asyncio
    async def test_zero_out_with_multiple_ids(self, mock_storage):
        """Test multiple IDs are preserved."""
        with patch("bindu.dspy.prompts._storage", mock_storage):
            await zero_out_all_except([5, 10, 15])
            mock_storage.zero_out_all_except.assert_called_with([5, 10, 15])


class TestEnsureSystemStable:
    """Test ensure_system_stable guard function."""

    @pytest.mark.asyncio
    async def test_ensure_stable_no_candidate(self):
        """Test passes if no candidate."""
        with patch("bindu.dspy.guard.get_candidate_prompt", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            # Should not raise
            await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_ensure_stable_with_candidate_raises(self):
        """Test raises RuntimeError if candidate exists."""
        with patch("bindu.dspy.guard.get_candidate_prompt", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": 2, "status": "candidate"}

            with pytest.raises(RuntimeError, match="DSPy training blocked"):
                await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_ensure_stable_calls_get_candidate(self):
        """Test calls get_candidate_prompt."""
        with patch("bindu.dspy.guard.get_candidate_prompt", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            await ensure_system_stable()
            mock_get.assert_called_once()


class TestSelectPromptWithCanary:
    """Test select_prompt_with_canary function."""

    @pytest.mark.asyncio
    async def test_select_no_prompts(self):
        """Test returns None if no prompts."""
        with patch("bindu.dspy.prompt_selector.get_active_prompt", new_callable=AsyncMock) as mock_active:
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", new_callable=AsyncMock) as mock_candidate:
                mock_active.return_value = None
                mock_candidate.return_value = None
                result = await select_prompt_with_canary()
                assert result is None

    @pytest.mark.asyncio
    async def test_select_only_active(self):
        """Test returns active if no candidate."""
        with patch("bindu.dspy.prompt_selector.get_active_prompt", new_callable=AsyncMock) as mock_active:
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", new_callable=AsyncMock) as mock_candidate:
                mock_active.return_value = {"id": 1, "traffic": 1.0}
                mock_candidate.return_value = None
                result = await select_prompt_with_canary()
                assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_select_only_candidate(self):
        """Test returns candidate if no active."""
        with patch("bindu.dspy.prompt_selector.get_active_prompt", new_callable=AsyncMock) as mock_active:
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", new_callable=AsyncMock) as mock_candidate:
                mock_active.return_value = None
                mock_candidate.return_value = {"id": 2, "traffic": 1.0}
                result = await select_prompt_with_canary()
                assert result["id"] == 2

    @pytest.mark.asyncio
    async def test_select_weighted_random(self):
        """Test weighted random selection logic."""
        with patch("bindu.dspy.prompt_selector.get_active_prompt", new_callable=AsyncMock) as mock_active:
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", new_callable=AsyncMock) as mock_candidate:
                with patch("bindu.dspy.prompt_selector.random.random") as mock_random:
                    mock_active.return_value = {"id": 1, "traffic": 0.9}
                    mock_candidate.return_value = {"id": 2, "traffic": 0.1}
                    mock_random.return_value = 0.05  # Should select active
                    result = await select_prompt_with_canary()
                    assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_select_zero_traffic(self):
        """Test defaults to active if both have 0 traffic."""
        with patch("bindu.dspy.prompt_selector.get_active_prompt", new_callable=AsyncMock) as mock_active:
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", new_callable=AsyncMock) as mock_candidate:
                mock_active.return_value = {"id": 1, "traffic": 0.0}
                mock_candidate.return_value = {"id": 2, "traffic": 0.0}
                result = await select_prompt_with_canary()
                assert result["id"] == 1
