"""Part type conversion utilities for worker operations."""

from __future__ import annotations

from typing import Any

from bindu.common.protocol.types import DataPart, FilePart, Part, TextPart


class PartConverter:
    """Optimized converter for Part type transformations."""

    # Part type mapping for efficient lookup
    PART_TYPES = {
        "text": (TextPart, "text"),
        "file": (FilePart, "file"),
        "data": (DataPart, "data"),
    }

    @staticmethod
    def dict_to_part(data: dict[str, Any]) -> Part:
        """Convert dictionary to appropriate Part type.

        Args:
            data: Dictionary representing a Part

        Returns:
            Appropriate Part type (TextPart, FilePart, or DataPart)
        """
        kind = data.get("kind")

        if kind in PartConverter.PART_TYPES:
            part_class, required_field = PartConverter.PART_TYPES[kind]
            if required_field in data:
                return part_class(**data)

        # Fallback: convert unknown dict to DataPart
        # DataPart requires 'text' field even though it's a data part
        return DataPart(kind="data", data=data, text="")

    @staticmethod
    def result_to_parts(result: Any) -> list[Part]:
        """Convert result to list of Parts with optimized type checking."""
        # Fast path for strings
        if isinstance(result, str):
            return [TextPart(kind="text", text=result)]

        # Handle sequences
        if isinstance(result, (list, tuple)):
            # Check if all items are strings (common case)
            if result and all(isinstance(item, str) for item in result):
                return [TextPart(kind="text", text=item) for item in result]

            # Handle mixed types
            parts: list[Part] = []
            for item in result:
                if isinstance(item, str):
                    parts.append(TextPart(kind="text", text=item))
                elif isinstance(item, dict):
                    parts.append(PartConverter.dict_to_part(item))
                else:
                    parts.append(TextPart(kind="text", text=str(item)))
            return parts

        # Handle dictionaries
        if isinstance(result, dict):
            return [PartConverter.dict_to_part(result)]

        # Fallback: convert to text
        return [TextPart(kind="text", text=str(result))]
