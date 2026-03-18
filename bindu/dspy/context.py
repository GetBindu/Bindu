# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose     |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Async context management for DSPy integration.

This module provides thread-safe context variables for passing prompt metadata
through the async call chain without modifying function signatures.
"""

from __future__ import annotations

from contextvars import ContextVar

# Thread-safe async context variable for storing the currently selected prompt ID
# This allows route_prompt to communicate the selected prompt_id to the worker
# without requiring changes to handler function signatures
current_prompt_id: ContextVar[str | None] = ContextVar('current_prompt_id', default=None)


def set_prompt_id(prompt_id: str | None) -> None:
    """Set the prompt ID for the current async context.
    
    This is called by route_prompt after selecting a prompt, making the ID
    available to the worker for database tracking.
    
    Args:
        prompt_id: The UUID of the selected prompt, or None to clear
    """
    current_prompt_id.set(prompt_id)


def get_prompt_id() -> str | None:
    """Get the prompt ID from the current async context.
    
    This is called by the worker to retrieve the prompt_id set by route_prompt,
    allowing it to update the task record in the database.
    
    Returns:
        The prompt ID if set, otherwise None
    """
    return current_prompt_id.get()


def clear_prompt_id() -> None:
    """Clear the prompt ID from the current async context.
    
    This should be called by the worker after processing to avoid leaking
    context between requests.
    """
    current_prompt_id.set(None)
