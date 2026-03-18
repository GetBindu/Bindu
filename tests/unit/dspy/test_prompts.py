"""Unit tests for bindu.dspy.prompts module.

Tests cover:
- Prompt class creation and persistence
- Async prompts CRUD operations
- Active and candidate prompt retrieval
- Traffic allocation management
"""

import sys
from unittest.mock import MagicMock

# Mock schema imports to avoid errors from missing 'text' import
sys.modules.setdefault("bindu.server.storage.schema", MagicMock())
sys.modules.setdefault("bindu.server.storage.postgres_storage", MagicMock())

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from bindu.dspy.prompts import (
    Prompt,
    get_active_prompt,
    get_candidate_prompt,
    insert_prompt,
    update_prompt_traffic,
    update_prompt_status,
    zero_out_all_except,
)


class TestPromptClass:
    """Test suite for Prompt class."""

    def test_prompt_creation(self):
        """Test creating a Prompt instance."""
        with patch("bindu.dspy.prompts.storage.insert_prompt_sync") as mock_insert:
            mock_insert.return_value = "prompt-id-123"

            prompt = Prompt("Test prompt text")

            assert prompt.id == "prompt-id-123"
            assert str(prompt) == "Test prompt text"

    def test_prompt_behaves_like_string(self):
        """Test that Prompt acts like a string."""
        with patch("bindu.dspy.prompts.storage.insert_prompt_sync") as mock_insert:
            mock_insert.return_value = "id"

            prompt = Prompt("Hello world")

            # Should be usable as string
            assert len(prompt) == 11
            assert "Hello" in prompt
            assert prompt.upper() == "HELLO WORLD"

    def test_prompt_with_custom_status(self):
        """Test creating a Prompt with custom status."""
        with patch("bindu.dspy.prompts.storage.insert_prompt_sync") as mock_insert:
            mock_insert.return_value = "id"

            prompt = Prompt("Text", status="candidate", traffic=0.2)

            assert prompt.status == "candidate"
            assert prompt.traffic == 0.2

    def test_prompt_saves_to_storage(self):
        """Test that Prompt saves itself to storage."""
        with patch("bindu.dspy.prompts.storage.insert_prompt_sync") as mock_insert:
            mock_insert.return_value = "id"

            Prompt("Prompt text", status="active", traffic=1.0)

            mock_insert.assert_called_once_with("Prompt text", "active", 1.0)

    def test_prompt_string_conversion(self):
        """Test string conversion."""
        with patch("bindu.dspy.prompts.storage.insert_prompt_sync") as mock_insert:
            mock_insert.return_value = "id"

            prompt = Prompt("Test")
            result = str(prompt)

            assert result == "Test"


class TestAsyncPromptOperations:
    """Test suite for async prompt operations."""

    @pytest.mark.asyncio
    async def test_get_active_prompt(self):
        """Test retrieving active prompt."""
        active_dict = {"id": "act-1", "prompt_text": "Active prompt"}

        with patch(
            "bindu.dspy.prompts.storage.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active_dict,
        ):

            result = await get_active_prompt()
            assert result == active_dict

    @pytest.mark.asyncio
    async def test_get_active_prompt_none(self):
        """Test retrieving active prompt when none exists."""
        with patch(
            "bindu.dspy.prompts.storage.get_active_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ):

            result = await get_active_prompt()
            assert result is None

    @pytest.mark.asyncio
    async def test_get_candidate_prompt(self):
        """Test retrieving candidate prompt."""
        candidate_dict = {"id": "cand-1", "prompt_text": "Candidate prompt"}

        with patch(
            "bindu.dspy.prompts.storage.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate_dict,
        ):

            result = await get_candidate_prompt()
            assert result == candidate_dict

    @pytest.mark.asyncio
    async def test_get_candidate_prompt_none(self):
        """Test retrieving candidate prompt when none exists."""
        with patch(
            "bindu.dspy.prompts.storage.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=None,
        ):

            result = await get_candidate_prompt()
            assert result is None

    @pytest.mark.asyncio
    async def test_insert_prompt(self):
        """Test inserting a new prompt."""
        with patch(
            "bindu.dspy.prompts.storage.insert_prompt",
            new_callable=AsyncMock,
            return_value="new-id-123",
        ):

            result = await insert_prompt("New prompt", "active", 1.0)

            assert result == "new-id-123"

    @pytest.mark.asyncio
    async def test_update_prompt_traffic(self):
        """Test updating prompt traffic."""
        with patch(
            "bindu.dspy.prompts.storage.update_prompt_traffic",
            new_callable=AsyncMock,
        ) as mock_update:

            await update_prompt_traffic("prompt-id", 0.5)

            mock_update.assert_called_once_with("prompt-id", 0.5)

    @pytest.mark.asyncio
    async def test_update_prompt_status(self):
        """Test updating prompt status."""
        with patch(
            "bindu.dspy.prompts.storage.update_prompt_status",
            new_callable=AsyncMock,
        ) as mock_update:

            await update_prompt_status("prompt-id", "deprecated")

            mock_update.assert_called_once_with("prompt-id", "deprecated")

    @pytest.mark.asyncio
    async def test_zero_out_all_except(self):
        """Test zeroing traffic for all except specified prompts."""
        prompt_ids = ["keep-1", "keep-2"]

        with patch(
            "bindu.dspy.prompts.storage.zero_out_all_except",
            new_callable=AsyncMock,
        ) as mock_zero:

            await zero_out_all_except(prompt_ids)

            mock_zero.assert_called_once_with(prompt_ids)

    @pytest.mark.asyncio
    async def test_zero_out_empty_list(self):
        """Test zeroing out with empty list."""
        with patch(
            "bindu.dspy.prompts.storage.zero_out_all_except",
            new_callable=AsyncMock,
        ) as mock_zero:

            await zero_out_all_except([])

            mock_zero.assert_called_once_with([])


class TestPromptIntegration:
    """Integration tests for prompt operations."""

    @pytest.mark.asyncio
    async def test_get_both_prompts_concurrently(self):
        """Test getting both active and candidate prompts."""
        active = {"id": "a1", "prompt_text": "Active"}
        candidate = {"id": "c1", "prompt_text": "Candidate"}

        with patch(
            "bindu.dspy.prompts.storage.get_active_prompt",
            new_callable=AsyncMock,
            return_value=active,
        ), patch(
            "bindu.dspy.prompts.storage.get_candidate_prompt",
            new_callable=AsyncMock,
            return_value=candidate,
        ):

            active_result = await get_active_prompt()
            candidate_result = await get_candidate_prompt()

            assert active_result == active
            assert candidate_result == candidate

    @pytest.mark.asyncio
    async def test_insert_and_get_workflow(self):
        """Test workflow of inserting and retrieving prompt."""
        inserted_id = "inserted-id"

        with patch(
            "bindu.dspy.prompts.storage.insert_prompt",
            new_callable=AsyncMock,
            return_value=inserted_id,
        ), patch(
            "bindu.dspy.prompts.storage.get_active_prompt",
            new_callable=AsyncMock,
            return_value={"id": inserted_id, "prompt_text": "New prompt"},
        ):

            # Insert
            result_id = await insert_prompt("New prompt", "active", 1.0)
            assert result_id == inserted_id

            # Retrieve
            prompt = await get_active_prompt()
            assert prompt["id"] == inserted_id
