"""Unit tests for DSPy prompt management, selection, and stability guards.

This module tests:
- Prompt CRUD operations (prompts.py)
- Weighted random prompt selection (prompt_selector.py)
- System stability guards (guard.py)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from bindu.dspy.prompts import (
    get_active_prompt,
    get_candidate_prompt,
    insert_prompt,
    update_prompt_traffic,
    update_prompt_status,
    zero_out_all_except,
)
from bindu.dspy.prompt_selector import select_prompt_with_canary
from bindu.dspy.guard import ensure_system_stable


# =============================================================================
# Prompt Management Tests (prompts.py)
# =============================================================================


class TestPromptManagement:
    """Test prompt CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_active_prompt_success(self):
        """Test fetching active prompt from database."""
        expected_prompt = {
            "id": 1,
            "prompt_text": "You are a helpful assistant",
            "status": "active",
            "traffic": 1.0,
            "num_interactions": 100,
            "average_feedback_score": 0.85,
        }

        mock_storage = AsyncMock()
        mock_storage.get_active_prompt = AsyncMock(return_value=expected_prompt)

        result = await get_active_prompt(storage=mock_storage)

        assert result == expected_prompt
        mock_storage.get_active_prompt.assert_called_once()
        mock_storage.disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_active_prompt_not_found(self):
        """Test when no active prompt exists."""
        mock_storage = AsyncMock()
        mock_storage.get_active_prompt = AsyncMock(return_value=None)

        result = await get_active_prompt(storage=mock_storage)

        assert result is None
        mock_storage.get_active_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_prompt_creates_storage_when_none_provided(self):
        """Test that new storage is created and disconnected when not provided."""
        expected_prompt = {"id": 1, "prompt_text": "Test", "status": "active", "traffic": 1.0}

        with patch("bindu.dspy.prompts.PostgresStorage") as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.get_active_prompt = AsyncMock(return_value=expected_prompt)
            mock_storage_class.return_value = mock_storage

            result = await get_active_prompt(storage=None, did="test-did")

            assert result == expected_prompt
            mock_storage_class.assert_called_once_with(did="test-did")
            mock_storage.connect.assert_called_once()
            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_candidate_prompt_success(self):
        """Test fetching candidate prompt from database."""
        expected_prompt = {
            "id": 2,
            "prompt_text": "You are an expert assistant",
            "status": "candidate",
            "traffic": 0.1,
            "num_interactions": 10,
            "average_feedback_score": 0.90,
        }

        mock_storage = AsyncMock()
        mock_storage.get_candidate_prompt = AsyncMock(return_value=expected_prompt)

        result = await get_candidate_prompt(storage=mock_storage)

        assert result == expected_prompt
        mock_storage.get_candidate_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_candidate_prompt_not_found(self):
        """Test when no candidate prompt exists."""
        mock_storage = AsyncMock()
        mock_storage.get_candidate_prompt = AsyncMock(return_value=None)

        result = await get_candidate_prompt(storage=mock_storage)

        assert result is None

    @pytest.mark.asyncio
    async def test_insert_prompt_success(self):
        """Test inserting new prompt with valid data."""
        mock_storage = AsyncMock()
        mock_storage.insert_prompt = AsyncMock(return_value=42)

        prompt_id = await insert_prompt(
            text="New prompt text",
            status="candidate",
            traffic=0.1,
            storage=mock_storage,
        )

        assert prompt_id == 42
        mock_storage.insert_prompt.assert_called_once_with("New prompt text", "candidate", 0.1)

    @pytest.mark.asyncio
    async def test_insert_prompt_with_did(self):
        """Test inserting prompt with DID isolation."""
        with patch("bindu.dspy.prompts.PostgresStorage") as mock_storage_class:
            mock_storage = AsyncMock()
            mock_storage.insert_prompt = AsyncMock(return_value=99)
            mock_storage_class.return_value = mock_storage

            prompt_id = await insert_prompt(
                text="Test prompt",
                status="active",
                traffic=1.0,
                storage=None,
                did="agent-123",
            )

            assert prompt_id == 99
            mock_storage_class.assert_called_once_with(did="agent-123")
            mock_storage.connect.assert_called_once()
            mock_storage.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_prompt_traffic(self):
        """Test updating traffic allocation."""
        mock_storage = AsyncMock()
        mock_storage.update_prompt_traffic = AsyncMock()

        await update_prompt_traffic(prompt_id=1, traffic=0.5, storage=mock_storage)

        mock_storage.update_prompt_traffic.assert_called_once_with(1, 0.5)

    @pytest.mark.asyncio
    async def test_update_prompt_status(self):
        """Test updating prompt status."""
        mock_storage = AsyncMock()
        mock_storage.update_prompt_status = AsyncMock()

        await update_prompt_status(prompt_id=1, status="deprecated", storage=mock_storage)

        mock_storage.update_prompt_status.assert_called_once_with(1, "deprecated")

    @pytest.mark.asyncio
    async def test_zero_out_all_except(self):
        """Test zeroing traffic for non-specified prompts."""
        mock_storage = AsyncMock()
        mock_storage.zero_out_all_except = AsyncMock()

        await zero_out_all_except(prompt_ids=[1, 2], storage=mock_storage)

        mock_storage.zero_out_all_except.assert_called_once_with([1, 2])


# =============================================================================
# Prompt Selection Tests (prompt_selector.py)
# =============================================================================


class TestPromptSelection:
    """Test weighted random prompt selection for canary deployment."""

    @pytest.mark.asyncio
    async def test_select_both_prompts_exist(self):
        """Test weighted random selection with both prompts."""
        active_prompt = {
            "id": 1,
            "prompt_text": "Active prompt",
            "status": "active",
            "traffic": 0.9,
        }
        candidate_prompt = {
            "id": 2,
            "prompt_text": "Candidate prompt",
            "status": "candidate",
            "traffic": 0.1,
        }

        with patch("bindu.dspy.prompt_selector.get_active_prompt", AsyncMock(return_value=active_prompt)):
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", AsyncMock(return_value=candidate_prompt)):
                # Test that we get a prompt back (either active or candidate)
                result = await select_prompt_with_canary()
                assert result is not None
                assert result["id"] in [1, 2]
                assert result["status"] in ["active", "candidate"]

    @pytest.mark.asyncio
    async def test_select_only_active_exists(self):
        """Test selection when only active exists."""
        active_prompt = {
            "id": 1,
            "prompt_text": "Active prompt",
            "status": "active",
            "traffic": 1.0,
        }

        with patch("bindu.dspy.prompt_selector.get_active_prompt", AsyncMock(return_value=active_prompt)):
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", AsyncMock(return_value=None)):
                result = await select_prompt_with_canary()

                assert result == active_prompt

    @pytest.mark.asyncio
    async def test_select_only_candidate_exists(self):
        """Test selection when only candidate exists (edge case)."""
        candidate_prompt = {
            "id": 2,
            "prompt_text": "Candidate prompt",
            "status": "candidate",
            "traffic": 1.0,
        }

        with patch("bindu.dspy.prompt_selector.get_active_prompt", AsyncMock(return_value=None)):
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", AsyncMock(return_value=candidate_prompt)):
                result = await select_prompt_with_canary()

                assert result == candidate_prompt

    @pytest.mark.asyncio
    async def test_select_no_prompts_exist(self):
        """Test when no prompts exist (returns None)."""
        with patch("bindu.dspy.prompt_selector.get_active_prompt", AsyncMock(return_value=None)):
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", AsyncMock(return_value=None)):
                result = await select_prompt_with_canary()

                assert result is None

    @pytest.mark.asyncio
    async def test_select_both_zero_traffic(self):
        """Test when both have 0 traffic (defaults to active)."""
        active_prompt = {
            "id": 1,
            "prompt_text": "Active prompt",
            "status": "active",
            "traffic": 0.0,
        }
        candidate_prompt = {
            "id": 2,
            "prompt_text": "Candidate prompt",
            "status": "candidate",
            "traffic": 0.0,
        }

        with patch("bindu.dspy.prompt_selector.get_active_prompt", AsyncMock(return_value=active_prompt)):
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", AsyncMock(return_value=candidate_prompt)):
                result = await select_prompt_with_canary()

                assert result == active_prompt

    @pytest.mark.asyncio
    async def test_select_traffic_weighting_distribution(self):
        """Test traffic weighting distribution (90/10 split verification)."""
        active_prompt = {
            "id": 1,
            "prompt_text": "Active prompt",
            "status": "active",
            "traffic": 0.9,
        }
        candidate_prompt = {
            "id": 2,
            "prompt_text": "Candidate prompt",
            "status": "candidate",
            "traffic": 0.1,
        }

        with patch("bindu.dspy.prompt_selector.get_active_prompt", AsyncMock(return_value=active_prompt)):
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", AsyncMock(return_value=candidate_prompt)):
                # Run selection many times and verify distribution
                active_count = 0
                candidate_count = 0
                iterations = 1000

                for _ in range(iterations):
                    result = await select_prompt_with_canary()
                    if result["id"] == 1:
                        active_count += 1
                    else:
                        candidate_count += 1

                # Allow 10% margin of error
                active_ratio = active_count / iterations
                candidate_ratio = candidate_count / iterations

                assert 0.80 <= active_ratio <= 1.0  # Should be ~90%
                assert 0.0 <= candidate_ratio <= 0.20  # Should be ~10%

    @pytest.mark.asyncio
    async def test_select_with_did_isolation(self):
        """Test DID isolation (different schemas)."""
        active_prompt = {
            "id": 1,
            "prompt_text": "Active prompt for agent-123",
            "status": "active",
            "traffic": 1.0,
        }

        with patch("bindu.dspy.prompt_selector.get_active_prompt", AsyncMock(return_value=active_prompt)) as mock_active:
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", AsyncMock(return_value=None)) as mock_candidate:
                result = await select_prompt_with_canary(did="agent-123")

                assert result == active_prompt
                # Verify DID was passed to both get functions
                mock_active.assert_called_once_with(storage=None, did="agent-123")
                mock_candidate.assert_called_once_with(storage=None, did="agent-123")

    @pytest.mark.asyncio
    async def test_select_with_storage_reuse(self):
        """Test that provided storage is reused."""
        active_prompt = {"id": 1, "status": "active", "traffic": 1.0, "prompt_text": "Test"}
        mock_storage = AsyncMock()

        with patch("bindu.dspy.prompt_selector.get_active_prompt", AsyncMock(return_value=active_prompt)) as mock_active:
            with patch("bindu.dspy.prompt_selector.get_candidate_prompt", AsyncMock(return_value=None)) as mock_candidate:
                await select_prompt_with_canary(storage=mock_storage)

                # Verify storage was passed to both get functions
                mock_active.assert_called_once_with(storage=mock_storage, did=None)
                mock_candidate.assert_called_once_with(storage=mock_storage, did=None)


# =============================================================================
# System Stability Guard Tests (guard.py)
# =============================================================================


class TestSystemStabilityGuard:
    """Test system stability checks before training."""

    @pytest.mark.asyncio
    async def test_ensure_system_stable_no_candidate(self):
        """Test when no candidate exists (stable system)."""
        with patch("bindu.dspy.guard.get_candidate_prompt", AsyncMock(return_value=None)):
            # Should not raise
            await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_ensure_system_stable_candidate_exists(self):
        """Test when candidate exists (blocks training)."""
        candidate = {
            "id": 99,
            "prompt_text": "Candidate being tested",
            "status": "candidate",
            "traffic": 0.1,
        }

        with patch("bindu.dspy.guard.get_candidate_prompt", AsyncMock(return_value=candidate)):
            with pytest.raises(RuntimeError, match="DSPy training blocked"):
                await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_ensure_system_stable_error_includes_id(self):
        """Test error message includes candidate ID."""
        candidate = {
            "id": 42,
            "prompt_text": "Test candidate",
            "status": "candidate",
            "traffic": 0.2,
        }

        with patch("bindu.dspy.guard.get_candidate_prompt", AsyncMock(return_value=candidate)):
            with pytest.raises(RuntimeError, match="id=42"):
                await ensure_system_stable()

    @pytest.mark.asyncio
    async def test_ensure_system_stable_with_did(self):
        """Test with DID isolation."""
        with patch("bindu.dspy.guard.get_candidate_prompt", AsyncMock(return_value=None)) as mock_get:
            await ensure_system_stable(did="agent-xyz")

            # Verify DID was passed
            mock_get.assert_called_once_with(storage=None, did="agent-xyz")

    @pytest.mark.asyncio
    async def test_ensure_system_stable_with_storage(self):
        """Test with provided storage instance."""
        mock_storage = AsyncMock()

        with patch("bindu.dspy.guard.get_candidate_prompt", AsyncMock(return_value=None)) as mock_get:
            await ensure_system_stable(storage=mock_storage)

            # Verify storage was passed
            mock_get.assert_called_once_with(storage=mock_storage, did=None)
