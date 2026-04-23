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
    """Resolve the *parent* directory into which DID keys should be stored.

    Returns the directory that will contain the ``subdir`` key folder — NOT
    the key folder itself. The caller (``initialize_did_extension``) is
    responsible for appending ``subdir`` to create the actual key storage
    path. Keeping that responsibility in one place avoids double-appending
    and mirrors what the settings module already does (``app_settings.did.pki_dir``
    is appended inside ``initialize_did_extension``).

    Priority order:
    1. ``explicit_dir`` if provided — user knows exactly where keys should live.
    2. ``caller_dir`` if provided — inferred from the calling script's location.
    3. Current working directory — last-ditch fallback, logs at INFO so
       operators notice when detection failed.

    Args:
        explicit_dir: Explicitly specified parent directory (highest priority).
        caller_dir: Directory of the calling script.
        subdir: Subdirectory name for keys (default: ``.bindu``). Kept in the
            signature for API compatibility and so callers can see which
            subdirectory the downstream code will create, but **not appended
            to the return value** — see the module docstring.

    Returns:
        Resolved parent ``Path``. Keys end up at ``<return value>/<subdir>``
        after ``initialize_did_extension`` appends ``subdir``.

    Historical note:
        Before this was made consistent, the explicit-dir branch returned
        its argument as-is while the caller-dir and fallback branches
        returned ``dir/subdir``. Callers (bindufy) compensated with
        ``.parent``, which only canceled the append in the caller/fallback
        branches — for explicit_dir it dropped a level too high and keys
        ended up in ``<caller_dir>.parent/.bindu`` instead of
        ``<caller_dir>/.bindu``. Now every branch returns a parent.
    """
    del subdir  # Intentionally unused — see docstring.

    if explicit_dir is not None:
        key_dir = Path(explicit_dir)
        logger.debug(f"Using explicit key directory: {key_dir}")
        return key_dir

    if caller_dir is not None:
        logger.debug(f"Using caller-based key directory: {caller_dir}")
        return caller_dir

    # Final fallback to cwd — log at INFO so operators see it when caller
    # detection fails (e.g. REPL/notebook).
    cwd = Path.cwd()
    logger.info(f"Using cwd-based key directory: {cwd}")
    return cwd
