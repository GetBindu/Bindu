"""Security utilities for storage operations."""

import re


def mask_database_url(url: str) -> str:
    """Mask password in database URL for safe logging.

    Args:
        url: Database URL (e.g., postgresql+asyncpg://user:password@host:port/db)  # pragma: allowlist secret

    Returns:
        URL with password masked (e.g., postgresql+asyncpg://user:***@host:port/db)  # pragma: allowlist secret
    """
    try:
        if "://" in url and "@" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                auth, host_part = rest.rsplit("@", 1)
                if ":" in auth:
                    user, _ = auth.split(":", 1)
                    return f"{scheme}://{user}:***@{host_part}"
        return url
    except Exception:
        return url


def sanitize_identifier(identifier: str) -> str:
    """Sanitize SQL identifier to prevent SQL injection.

    Validates that identifier contains only alphanumeric characters and underscores.

    Args:
        identifier: SQL identifier to sanitize (e.g., schema name, table name)

    Returns:
        Sanitized identifier (unchanged if valid)

    Raises:
        ValueError: If identifier contains invalid characters
    """
    if not re.match(r"^[a-zA-Z0-9_]+$", identifier):
        raise ValueError(
            f"Invalid identifier: {identifier}. Must contain only alphanumeric characters and underscores."
        )
    return identifier
