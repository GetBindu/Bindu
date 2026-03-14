"""Unit tests for bindu.dspy.prompt_router module.

Tests cover:
- Prompt routing logic
- Weighted random selection
- Context setting
- A/B testing scenarios
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from unittest.mock import patch, AsyncMock
import random

from bindu.dspy.prompt_router import route_prompt


class TestPromptRouter:
    """Test suite for prompt routing functionality."""

    @pytest.mark.asyncio
    async def test_route_prompt_no_prompts_with_initial(self):
        """Test routing when no prompts exist but initial is provided."""
        initial = "Initial system prompt"

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "bindu.dspy.prompt_router.storage.insert_prompt",
            new_callable=AsyncMock,
            return_value="new-prompt-id",
        ), patch("bindu.dspy.prompt_router.set_prompt_id"):

            result = await route_prompt(initial_prompt=initial)
            assert result == initial

    @pytest.mark.asyncio
    async def test_route_prompt_no_prompts_without_initial(self):
        """Test routing when no prompts and no initial provided."""
        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch("bindu.dspy.prompt_router.set_prompt_id"):

            result = await route_prompt(initial_prompt=None)
            assert result == ""

    @pytest.mark.asyncio
    async def test_route_prompt_only_active(self):
        """Test routing when only active prompt exists."""
        active = {"id": "active-1", "prompt_text": "Active prompt", "traffic": 1.0}

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "bindu.dspy.prompt_router.set_prompt_id"
        ) as mock_set:

            result = await route_prompt()
            assert result == "Active prompt"
            mock_set.assert_called_once_with(active["id"])

    @pytest.mark.asyncio
    async def test_route_prompt_only_candidate(self):
        """Test routing when only candidate prompt exists."""
        candidate = {"id": "cand-1", "prompt_text": "Candidate prompt", "traffic": 0.2}

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ), patch(
            "bindu.dspy.prompt_router.set_prompt_id"
        ) as mock_set:

            result = await route_prompt()
            assert result == "Candidate prompt"
            mock_set.assert_called_once_with(candidate["id"])

    @pytest.mark.asyncio
    async def test_route_prompt_weighted_selection_deterministic(self):
        """Test weighted selection with deterministic mock."""
        active = {"id": "a1", "prompt_text": "Active", "traffic": 0.9}
        candidate = {"id": "c1", "prompt_text": "Candidate", "traffic": 0.1}

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ), patch(
            "bindu.dspy.prompt_router.random.random", return_value=0.5
        ), patch(
            "bindu.dspy.prompt_router.set_prompt_id"
        ) as mock_set:

            result = await route_prompt()
            # With roll=0.5 and active_traffic/(total)=0.9/1.0=0.9
            # 0.5 < 0.9, so should select active
            assert result == "Active"
            mock_set.assert_called_once_with("a1")

    @pytest.mark.asyncio
    async def test_route_prompt_weighted_selection_candidate_wins(self):
        """Test weighted selection when candidate is selected."""
        active = {"id": "a1", "prompt_text": "Active", "traffic": 0.2}
        candidate = {"id": "c1", "prompt_text": "Candidate", "traffic": 0.8}

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ), patch(
            "bindu.dspy.prompt_router.random.random", return_value=0.8
        ), patch(
            "bindu.dspy.prompt_router.set_prompt_id"
        ) as mock_set:

            result = await route_prompt()
            # With roll=0.8 and active_traffic/(total)=0.2/1.0=0.2
            # 0.8 >= 0.2, so should select candidate
            assert result == "Candidate"
            mock_set.assert_called_once_with("c1")

    @pytest.mark.asyncio
    async def test_route_prompt_zero_traffic_both(self):
        """Test routing when both have zero traffic."""
        active = {"id": "a1", "prompt_text": "Active", "traffic": 0.0}
        candidate = {"id": "c1", "prompt_text": "Candidate", "traffic": 0.0}

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ), patch(
            "bindu.dspy.prompt_router.set_prompt_id"
        ) as mock_set:

            result = await route_prompt()
            # Should default to active when both have 0 traffic
            assert result == "Active"
            mock_set.assert_called_once_with("a1")

    @pytest.mark.asyncio
    async def test_route_prompt_sets_context(self):
        """Test that routing sets prompt ID in context."""
        active = {"id": "ctx-prompt-123", "prompt_text": "Prompt", "traffic": 1.0}

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "bindu.dspy.prompt_router.set_prompt_id"
        ) as mock_set:

            await route_prompt()
            mock_set.assert_called_once_with("ctx-prompt-123")

    @pytest.mark.asyncio
    async def test_route_prompt_initial_creates_prompt(self):
        """Test that initial prompt is created when storage is empty."""
        initial = "New system prompt"

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "bindu.dspy.prompt_router.storage.insert_prompt",
            new_callable=AsyncMock,
            return_value="generated-id",
        ) as mock_insert, patch(
            "bindu.dspy.prompt_router.set_prompt_id"
        ):

            await route_prompt(initial_prompt=initial)
            mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_route_prompt_normalization_traffic_weights(self):
        """Test that traffic weights are normalized correctly."""
        # Non-standard traffic values
        active = {"id": "a1", "prompt_text": "Active", "traffic": 3.0}
        candidate = {"id": "c1", "prompt_text": "Candidate", "traffic": 7.0}

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ), patch(
            "bindu.dspy.prompt_router.random.random", return_value=0.25
        ), patch(
            "bindu.dspy.prompt_router.set_prompt_id"
        ) as mock_set:

            await route_prompt()
            # Normalized: active=3/10=0.3, candidate=7/10=0.7
            # roll=0.25 < 0.3, select active
            assert mock_set.call_args[0][0] == "a1"

    @pytest.mark.asyncio
    async def test_route_prompt_large_text(self):
        """Test routing with large prompt text."""
        large_text = "A" * 10000
        active = {"id": "a1", "prompt_text": large_text, "traffic": 1.0}

        with patch(
            "bindu.dspy.prompt_router.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active,
        ), patch(
            "bindu.dspy.prompt_router.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ), patch("bindu.dspy.prompt_router.set_prompt_id"):

            result = await route_prompt()
            assert len(result) == 10000
