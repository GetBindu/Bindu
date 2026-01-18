"""bindu utilities and helper functions."""

from .capabilities import (
    add_extension_to_capabilities,
    get_x402_extension_from_capabilities,
)
from .config_loader import load_config_from_env, update_auth_settings
from .did_utils import check_did_match, validate_did_extension
from .env_loader import load_and_apply_env_file, load_env_file, resolve_path
from .path_resolver import (
    get_caller_directory,
    resolve_key_directory,
    ensure_directory_exists,
)
from .request_utils import handle_endpoint_errors
from .server_runner import run_server, setup_signal_handlers
from .skill_loader import load_skills
from .skill_utils import find_skill_by_id

# Note: worker_utils is NOT imported here to avoid circular dependency with DID extension
# Import directly from bindu.utils.worker_utils where needed

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
    # Environment utilities
    "load_env_file",
    "load_and_apply_env_file",
    "resolve_path",
    # Path utilities
    "get_caller_directory",
    "resolve_key_directory",
    "ensure_directory_exists",
    # Server utilities
    "run_server",
    "setup_signal_handlers",
    # Request utilities
    "handle_endpoint_errors",
]
