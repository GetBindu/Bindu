"""Pytest fixtures for DSPy unit tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from bindu.dspy.models import Interaction
from bindu.dspy.dataset import RawTaskData


@pytest.fixture
def mock_storage():
    """Mock PostgresStorage instance."""
    storage = AsyncMock()
    storage.connect = AsyncMock()
    storage.disconnect = AsyncMock()
    storage.fetch_tasks_with_feedback = AsyncMock(return_value=[])
    storage.get_active_prompt = AsyncMock(return_value=None)
    storage.get_candidate_prompt = AsyncMock(return_value=None)
    storage.insert_prompt = AsyncMock(return_value=1)
    storage.update_prompt_traffic = AsyncMock()
    storage.update_prompt_status = AsyncMock()
    storage.zero_out_all_except = AsyncMock()
    return storage


@pytest.fixture
def sample_interaction():
    """Create a sample Interaction for testing."""
    return Interaction(
        id=uuid4(),
        user_input="What is the capital of France?",
        agent_output="The capital of France is Paris.",
        feedback_score=0.9,
        feedback_type="rating",
    )


@pytest.fixture
def sample_raw_task():
    """Create a sample RawTaskData for testing."""
    return RawTaskData(
        id=uuid4(),
        history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        created_at="2026-01-28T00:00:00Z",
        feedback_data={"rating": 4},
    )


@pytest.fixture
def sample_messages():
    """Create sample cleaned messages."""
    return [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Second question"},
        {"role": "assistant", "content": "Second answer"},
    ]


@pytest.fixture
def mock_dspy_lm():
    """Mock dspy.LM for testing."""
    return MagicMock()


@pytest.fixture
def mock_optimizer():
    """Mock DSPy optimizer with compile method."""
    optimizer = MagicMock()
    optimizer.compile = MagicMock(return_value=MagicMock())
    return optimizer
