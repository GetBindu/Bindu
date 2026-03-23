"""Artifact building utilities for worker operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from bindu.common.protocol.types import Artifact, Part
from bindu.settings import app_settings

from .parts import PartConverter

if TYPE_CHECKING:
    from bindu.extensions.did import DIDAgentExtension


class ArtifactBuilder:
    """Optimized builder for creating artifacts from results."""

    @staticmethod
    def from_result(
        results: Any,
        artifact_name: str = "result",
        did_extension: Optional["DIDAgentExtension"] = None,
    ) -> list[Artifact]:
        """Convert execution result to protocol artifacts.

        Args:
            results: Result from manifest execution
            artifact_name: Name for the artifact
            did_extension: Optional DID extension for signing

        Returns:
            List of protocol artifacts
        """
        # Convert result to appropriate part type
        if isinstance(results, str):
            parts = [{"kind": "text", "text": results}]
        elif (
            isinstance(results, (list, tuple))
            and results
            and all(isinstance(item, str) for item in results)
        ):
            # Join streaming results efficiently
            parts = [{"kind": "text", "text": "\n".join(results)}]
        else:
            # Structured data
            parts = [{"kind": "data", "data": {"result": results}}]

        # Apply DID signing if available
        if did_extension:
            metadata_key = app_settings.did.agent_extension_metadata
            # Cast parts to list[dict[str, Any]] to allow metadata assignment
            from typing import cast

            typed_parts_list = cast(list[dict[str, Any]], parts)
            for part in typed_parts_list:
                if part.get("kind") == "text" and "text" in part:
                    text_value = part["text"]
                    if isinstance(text_value, str):
                        if "metadata" not in part:
                            part["metadata"] = {}
                        metadata = part["metadata"]
                        if isinstance(metadata, dict):
                            metadata[metadata_key] = did_extension.sign_text(text_value)
            parts = typed_parts_list

        # Convert dict parts to proper Part types for Artifact
        final_parts: list[Part] = [
            PartConverter.dict_to_part(p) if isinstance(p, dict) else p for p in parts
        ]
        return [Artifact(artifact_id=uuid4(), name=artifact_name, parts=final_parts)]
