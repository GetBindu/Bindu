"""Custom assertion helpers for common test patterns."""

from typing import Any, Optional
from uuid import UUID


def assert_task_state(task: dict[str, Any], expected_state: str) -> None:
    """Assert that a task has the expected state.

    Args:
        task: Task dictionary to check
        expected_state: Expected state value

    Raises:
        AssertionError: If state doesn't match
    """
    actual_state = task.get("state")
    assert actual_state == expected_state, (
        f"Expected task state '{expected_state}', got '{actual_state}'"
    )


def assert_jsonrpc_error(
    response: dict[str, Any], expected_code: Optional[int] = None
) -> None:
    """Assert that a JSON-RPC response contains an error.

    Args:
        response: JSON-RPC response dictionary
        expected_code: Optional expected error code

    Raises:
        AssertionError: If response is not an error or code doesn't match
    """
    assert "error" in response, "Expected JSON-RPC error response"

    if expected_code is not None:
        actual_code = response["error"].get("code")
        assert actual_code == expected_code, (
            f"Expected error code {expected_code}, got {actual_code}"
        )


def assert_jsonrpc_success(response: dict[str, Any]) -> None:
    """Assert that a JSON-RPC response is successful.

    Args:
        response: JSON-RPC response dictionary

    Raises:
        AssertionError: If response contains an error
    """
    assert "error" not in response, (
        f"Expected successful JSON-RPC response, got error: {response.get('error')}"
    )
    assert "result" in response, "Expected 'result' field in JSON-RPC response"


def assert_valid_uuid(value: str) -> None:
    """Assert that a string is a valid UUID.

    Args:
        value: String to validate as UUID

    Raises:
        AssertionError: If value is not a valid UUID
    """
    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError) as e:
        raise AssertionError(f"Expected valid UUID, got '{value}': {e}")


def assert_dict_contains(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    """Assert that actual dict contains all key-value pairs from expected dict.

    Args:
        actual: Dictionary to check
        expected: Dictionary with expected key-value pairs

    Raises:
        AssertionError: If any expected key-value pair is missing or different
    """
    for key, expected_value in expected.items():
        assert key in actual, f"Expected key '{key}' not found in dict"
        actual_value = actual[key]
        assert actual_value == expected_value, (
            f"For key '{key}': expected {expected_value}, got {actual_value}"
        )


def assert_list_length(actual: list, expected_length: int) -> None:
    """Assert that a list has the expected length.

    Args:
        actual: List to check
        expected_length: Expected number of items

    Raises:
        AssertionError: If length doesn't match
    """
    actual_length = len(actual)
    assert actual_length == expected_length, (
        f"Expected list length {expected_length}, got {actual_length}"
    )
