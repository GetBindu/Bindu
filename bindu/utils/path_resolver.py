"""Path resolution utilities for determining caller directories and key storage locations.

This module provides robust path resolution that works across different execution contexts
including REPL, Jupyter notebooks, frozen executables, and normal Python scripts.
"""

import inspect
import os
from pathlib import Path
from typing import Optional

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.path_resolver")


def get_caller_directory(
    frames_back: int = 2, fallback_to_cwd: bool = True
) -> Optional[Path]:
    """Get the directory of the calling code using frame inspection.

    Args:
        frames_back: Number of frames to go back in the call stack (default: 2)
        fallback_to_cwd: If True, return cwd when frame inspection fails

    Returns:
        Path to caller's directory, or None if detection fails and fallback disabled
    """
    try:
        frame = inspect.currentframe()
        if not frame:
            raise RuntimeError("No frame available")

        # Walk back the specified number of frames
        for _ in range(frames_back):
            if frame.f_back:
                frame = frame.f_back
            else:
                raise RuntimeError("Not enough frames in call stack")

        caller_file = inspect.getframeinfo(frame).filename
        caller_dir = Path(os.path.abspath(caller_file)).parent

        logger.debug(f"Detected caller directory from frame: {caller_dir}")
        return caller_dir

    except (AttributeError, OSError, RuntimeError) as e:
        logger.debug(f"Frame inspection failed: {e}")

        if fallback_to_cwd:
            cwd = Path.cwd()
            logger.info(
                f"Using current working directory as fallback: {cwd} "
                f"(frame inspection unavailable in REPL/notebook/frozen executable)"
            )
            return cwd

        return None


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


def ensure_directory_exists(path: Path, create: bool = True) -> Path:
    """Ensure a directory exists, optionally creating it.

    Args:
        path: Directory path to check/create
        create: If True, create directory if it doesn't exist

    Returns:
        The directory path

    Raises:
        FileNotFoundError: If directory doesn't exist and create=False
    """
    if not path.exists():
        if create:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {path}")
        else:
            raise FileNotFoundError(f"Directory does not exist: {path}")

    return path
