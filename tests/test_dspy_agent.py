"""
Tests for the DSPy agent example.

WHAT IS TESTED:
    - handler() returns correct message format
    - handler() uses only the last message
    - handler() returns assistant role
    - handler() returns non-empty response
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_qa_program():
    """Mock qa_program so tests don't need a real OpenAI key."""
    with patch("examples.dspy_agent.qa_program") as mock_program:
        mock_result = MagicMock()
        mock_result.answer = "The capital of France is Paris."
        mock_program.return_value = mock_result
        yield mock_program


def test_handler_returns_list(mock_qa_program):
    """Handler must return a list."""
    from examples.dspy_agent import handler
    messages = [{"role": "user", "content": "What is the capital of France?"}]
    result = handler(messages)
    assert isinstance(result, list)


def test_handler_returns_assistant_role(mock_qa_program):
    """Response must have role = assistant."""
    from examples.dspy_agent import handler
    messages = [{"role": "user", "content": "What is the capital of France?"}]
    result = handler(messages)
    assert result[0]["role"] == "assistant"


def test_handler_returns_non_empty_content(mock_qa_program):
    """Response content must be a non-empty string."""
    from examples.dspy_agent import handler
    messages = [{"role": "user", "content": "What is the capital of France?"}]
    result = handler(messages)
    assert isinstance(result[0]["content"], str)
    assert len(result[0]["content"]) > 0


def test_handler_uses_last_message(mock_qa_program):
    """Handler must use only the last message in conversation."""
    from examples.dspy_agent import handler
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "What is 2 + 2?"},
    ]
    handler(messages)
    mock_qa_program.assert_called_once_with(question="What is 2 + 2?")