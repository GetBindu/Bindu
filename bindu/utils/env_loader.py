"""Environment variable loading utilities.

This module provides utilities for loading environment variables from .env files
and resolving file paths relative to caller locations.
"""

import os
from pathlib import Path
from typing import Dict

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.env_loader")


def load_env_file(env_file: str, base_dir: Path | None = None) -> Dict[str, str]:
    """Load environment variables from a .env file.

    Args:
        env_file: Path to .env file (relative or absolute)
        base_dir: Base directory for resolving relative paths. If None, uses cwd.

    Returns:
        Dictionary of environment variables loaded from file

    Raises:
        FileNotFoundError: If env_file doesn't exist
        ImportError: If python-dotenv is not installed
    """
    try:
        from dotenv import dotenv_values
    except ImportError:
        raise ImportError(
            "python-dotenv is required to load .env files. "
            "Install it with: pip install python-dotenv"
        )

    # Resolve path
    env_path = resolve_path(env_file, base_dir)

    if not env_path.exists():
        raise FileNotFoundError(f"Environment file not found: {env_path}")

    # Load env vars
    env_vars = dotenv_values(str(env_path))
    logger.info(f"Loaded {len(env_vars)} environment variables from: {env_path}")

    return {k: v for k, v in env_vars.items() if v is not None}


def apply_env_vars(env_vars: Dict[str, str], override_existing: bool = False) -> None:
    """Apply environment variables to os.environ.

    Args:
        env_vars: Dictionary of environment variables to apply
        override_existing: If True, override existing environment variables.
                          If False, only set variables that don't exist.
    """
    applied_count = 0
    for key, value in env_vars.items():
        if override_existing or key not in os.environ:
            os.environ[key] = value
            applied_count += 1

    logger.debug(f"Applied {applied_count}/{len(env_vars)} environment variables")


def resolve_path(path: str | Path, base_dir: Path | None = None) -> Path:
    """Resolve a path, handling both absolute and relative paths.

    Args:
        path: Path to resolve (can be string or Path object)
        base_dir: Base directory for resolving relative paths. If None, uses cwd.

    Returns:
        Resolved absolute Path object
    """
    path_obj = Path(path)

    # If already absolute, return as-is
    if path_obj.is_absolute():
        return path_obj

    # Resolve relative to base_dir or cwd
    base = base_dir if base_dir is not None else Path.cwd()
    return (base / path_obj).resolve()


def load_and_apply_env_file(
    env_file: str, base_dir: Path | None = None, override_existing: bool = False
) -> Dict[str, str]:
    """Load environment variables from file and apply them to os.environ.

    Convenience function combining load_env_file and apply_env_vars.

    Args:
        env_file: Path to .env file
        base_dir: Base directory for resolving relative paths
        override_existing: Whether to override existing environment variables

    Returns:
        Dictionary of loaded environment variables
    """
    env_vars = load_env_file(env_file, base_dir)
    apply_env_vars(env_vars, override_existing)
    return env_vars
