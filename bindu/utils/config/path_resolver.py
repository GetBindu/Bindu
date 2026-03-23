"""Path resolution utilities for configuration-related directories.

This module provides path resolution for DID key storage and other
configuration directories with intelligent fallback strategies.
"""

from pathlib import Path
from typing import Optional

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.config.path_resolver")


def resolve_key_directory(
    explicit_dir: Optional[str | Path] = None,
    caller_dir: Optional[Path] = None,
    subdir: str = ".bindu",
) -> Path:
    """Resolve the directory for storing DID keys with multiple fallback strategies.

    Priority order:
    1. Explicit directory if provided
    2. Caller directory + subdir if caller_dir provided
    3. Current working directory + subdir

    Args:
        explicit_dir: Explicitly specified key directory (highest priority)
        caller_dir: Directory of the calling script
        subdir: Subdirectory name for keys (default: ".bindu")

    Returns:
        Resolved Path for key storage
    """
    if explicit_dir is not None:
        key_dir = Path(explicit_dir)
        logger.debug(f"Using explicit key directory: {key_dir}")
        return key_dir

    if caller_dir is not None:
        key_dir = caller_dir / subdir
        logger.debug(f"Using caller-based key directory: {key_dir}")
        return key_dir

    # Final fallback to cwd
    key_dir = Path.cwd() / subdir
    logger.info(f"Using cwd-based key directory: {key_dir}")
    return key_dir
