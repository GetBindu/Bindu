"""Utilities for managing agent capabilities and extensions."""

from typing import Any, Dict, Optional

from bindu.common.protocol.types import AgentCapabilities


def add_extension_to_capabilities(
    capabilities: AgentCapabilities | Dict[str, Any] | None,
    extension: Any,
) -> AgentCapabilities:
    """Add an extension to agent capabilities.

    Args:
        capabilities: Existing capabilities (dict, AgentCapabilities object, or None)
        extension: Extension instance (X402AgentExtension or DIDAgentExtension)

    Returns:
        AgentCapabilities object with extension included, preserving all other fields

    """
    if capabilities is None:
        capabilities = {}
    
    # Ensure we're working with a dict (TypedDict is already a dict at runtime)
    if not isinstance(capabilities, dict):
        capabilities = {}
    
    # Get existing extensions and add new one
    extensions = capabilities.get("extensions", [])
    extensions.append(extension)
    
    # Preserve all existing capability fields and add extensions
    return AgentCapabilities(
        extensions=extensions,
        push_notifications=capabilities.get("push_notifications", False),
        streaming=capabilities.get("streaming", False),
    )


def get_x402_extension_from_capabilities(manifest: Any) -> Optional[Any]:
    """Extract X402 extension from manifest capabilities.

    Args:
        capabilities: Agent capabilities object with extensions

    Returns:
        X402AgentExtension instance if configured and required, None otherwise
    """
    from bindu.extensions.x402 import X402AgentExtension

    for ext in manifest.capabilities.get("extensions", []):
        # Check if it's already an X402AgentExtension instance
        if isinstance(ext, X402AgentExtension):
            return ext

    return None
