"""
Utility functions for error handling and logging
"""

import logging
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def log_agent_activity(
    session_id: str,
    agent_name: str,
    action: str,
    reasoning: str = None,
    state_snapshot: Dict[str, Any] = None,
):
    """Log agent activity (in-memory logging)"""
    logger.info(f"[{session_id}] {agent_name} - {action}: {reasoning}")


def safe_get_state_value(state: Dict[str, Any], key: str, default: Any = None):
    """Safely get value from state dictionary"""
    try:
        return state.get(key, default)
    except (AttributeError, TypeError):
        return default


def format_error_message(error: Exception) -> str:
    """Format error message for API responses"""
    error_type = type(error).__name__
    error_msg = str(error)
    return f"{error_type}: {error_msg}"
