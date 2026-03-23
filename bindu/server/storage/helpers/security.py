"""Security utilities for storage operations."""

from bindu.utils.logging import get_logger

logger = get_logger("bindu.storage.security")


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
    except (AttributeError, TypeError, ValueError) as error:
        logger.warning("Failed to mask database URL", error=str(error))
        return url


def sanitize_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifier to prevent SQL injection.

    Performs sanitization in a clear, step-by-step manner:
    - Strips leading/trailing whitespace
    - Checks for allowed characters (alphanumeric, underscore)
    - Raises ValueError if any invalid characters remain

    Args:
        identifier: SQL identifier to sanitize (e.g., schema name, table name)

    Returns:
        Sanitized identifier (unchanged if valid)

    Raises:
        ValueError: If identifier contains invalid characters
    """
    # Step 1: Remove leading and trailing whitespace
    sanitized = identifier.strip()

    # Step 2: Disallow empty identifiers after stripping
    if not sanitized:
        raise ValueError("Identifier cannot be empty or only whitespace.")

    # Step 3: Check for invalid characters (allow only letters, digits, underscores)
    invalid_chars = [c for c in sanitized if not (c.isalnum() or c == "_")]
    if invalid_chars:
        invalid_str = "".join(sorted(set(invalid_chars)))
        raise ValueError(
            f"Invalid identifier: {identifier}. "
            f"Contains invalid characters: '{invalid_str}'. "
            "Identifier must contain only alphanumeric characters and underscores."
        )

    # Step 4: Return sanitized identifier
    return sanitized
