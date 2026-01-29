"""UUID validation utilities for storage operations."""

from uuid import UUID


def validate_uuid_type(value: UUID | str | None, param_name: str) -> UUID:
    """Validate and convert a value to UUID type.

    Args:
        value: Value to validate (UUID, string, or None)
        param_name: Parameter name for error messages

    Returns:
        UUID: Validated UUID object

    Raises:
        TypeError: If value is None, invalid type, or invalid UUID string
    """
    if value is None:
        raise TypeError(f"{param_name} cannot be None")

    if isinstance(value, UUID):
        return value

    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError as e:
            raise TypeError(
                f"{param_name} must be a valid UUID string, got '{value}'"
            ) from e

    raise TypeError(f"{param_name} must be UUID or str, got {type(value).__name__}")
