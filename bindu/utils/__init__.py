"""Bindu utilities and helper functions.

Organized into focused packages:
- config: Configuration loading with DRY factory pattern
- http: HTTP clients (generic, auth, vault, tokens)
- did: DID signature and validation utilities
- worker: Worker operation utilities (messages, parts, artifacts, tasks)
- skills: Skill loading and management

Backward compatibility maintained through re-exports.
"""

# Core utilities (kept at top level)
from .capabilities import (
    add_extension_to_capabilities,
    get_x402_extension_from_capabilities,
)
from .exceptions import (
    HTTPError,
    HTTPConnectionError,
    HTTPTimeoutError,
    HTTPClientError,
    HTTPServerError,
)
from .retry import create_retry_decorator
from .server_runner import run_server, setup_signal_handlers

# Organized packages (new structure)
from .config import load_config_from_env, update_auth_settings
from .did import check_did_match, validate_did_extension
from .skills import load_skills, find_skill_by_id

# Note: worker package is NOT imported here to avoid circular dependency with DID extension
# Import directly from bindu.utils.worker where needed
# Note: http package contains http_client, hybrid_auth_client, vault_client, agent_token_utils
# Import directly from bindu.utils.http where needed

__all__ = [
    # Skill utilities
    "load_skills",
    "find_skill_by_id",
    # Capability utilities
    "add_extension_to_capabilities",
    "get_x402_extension_from_capabilities",
    # DID utilities
    "validate_did_extension",
    "check_did_match",
    # Configuration utilities
    "load_config_from_env",
    "update_auth_settings",
    # Exception types
    "HTTPError",
    "HTTPConnectionError",
    "HTTPTimeoutError",
    "HTTPClientError",
    "HTTPServerError",
    # Server utilities
    "run_server",
    "setup_signal_handlers",
    # Retry utilities
    "create_retry_decorator",
]
