"""Agent card endpoint for W3C-compliant agent discovery."""

from __future__ import annotations

from time import time
from typing import Any, cast
from uuid import UUID

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import AgentCard, AgentCapabilities, agent_card_ta
from bindu.server.applications import BinduApplication
from bindu.utils.logging import get_logger
from .utils import create_response_with_x402, handle_endpoint_errors, get_client_ip

logger = get_logger("bindu.server.endpoints.agent_card")

# Constants
A2A_PROTOCOL_VERSION = "1.0.0"
DEFAULT_AGENT_DESCRIPTION = "An AI agent exposed as an A2A agent."
DEFAULT_INPUT_MODES = ["text/plain", "application/json"]
DEFAULT_OUTPUT_MODES = ["text/plain", "application/json"]


def _serialize_extension(ext: Any) -> dict | None:
    """Serialize an extension to AgentExtension dict format.

    Args:
        ext: Extension instance or dict

    Returns:
        Serialized extension dict or None if unknown type
    """
    # Check if it's a DIDAgentExtension instance
    if hasattr(ext, "did") and hasattr(ext, "author"):
        return {
            "uri": f"did:{ext.did}" if not ext.did.startswith("did:") else ext.did,
            "description": f"DID-based identity for {ext.agent_name or 'agent'}",
            "required": False,
            "params": {
                "author": ext.author,
                "agent_name": ext.agent_name,
                "agent_id": ext.agent_id,
            },
        }
    elif isinstance(ext, dict):
        # Already in correct format
        return ext
    else:
        # Unknown extension type
        logger.warning(f"Unknown extension type: {type(ext)}, skipping")
        return None


def _serialize_extensions(capabilities: dict) -> None:
    """Serialize extensions in capabilities dict in-place.

    Args:
        capabilities: Capabilities dict to modify
    """
    if "extensions" not in capabilities:
        return

    serializable_extensions = []
    for ext in capabilities["extensions"]:
        serialized = _serialize_extension(ext)
        if serialized is not None:
            serializable_extensions.append(serialized)

    capabilities["extensions"] = serializable_extensions


def create_agent_card(app: BinduApplication) -> AgentCard:
    """Create agent card from application manifest.

    Args:
        app: BinduApplication instance

    Returns:
        AgentCard instance

    Note:
        Excludes skill documentation_content from agent card to reduce payload size.
        Full documentation is available via /agent/skills/{skill_id}/documentation
    """
    # Ensure manifest exists
    if app.manifest is None:
        raise ValueError("Application manifest is required to create agent card")

    # Store manifest in local variable for type narrowing
    manifest = app.manifest

    # Minimize skills to just id, name, and documentation_path (URL) - full details via dedicated endpoint
    minimal_skills = []
    for skill in manifest.skills:
        minimal_skills.append(
            {
                "id": skill["id"],
                "name": skill["name"],
                "documentation_path": f"{app.url}/agent/skills/{skill['id']}",
            }
        )

    # Ensure id is UUID type (convert from string if needed)
    agent_id = manifest.id if isinstance(manifest.id, UUID) else UUID(manifest.id)

    # Convert capabilities to serializable format
    capabilities = dict(manifest.capabilities)
    _serialize_extensions(capabilities)

    return AgentCard(
        id=agent_id,
        name=manifest.name,
        description=manifest.description or DEFAULT_AGENT_DESCRIPTION,
        url=app.url,
        version=app.version,
        protocol_version=A2A_PROTOCOL_VERSION,
        skills=minimal_skills,
        capabilities=cast(AgentCapabilities, capabilities),
        kind=manifest.kind,
        num_history_sessions=manifest.num_history_sessions,
        extra_data=manifest.extra_data
        or {"created": int(time()), "server_info": "bindu Agent Server"},
        debug_mode=manifest.debug_mode,
        debug_level=manifest.debug_level,
        monitoring=manifest.monitoring,
        telemetry=manifest.telemetry,
        agent_trust=manifest.agent_trust,
        default_input_modes=DEFAULT_INPUT_MODES,
        default_output_modes=DEFAULT_OUTPUT_MODES,
    )


@handle_endpoint_errors("agent card")
async def agent_card_endpoint(app: BinduApplication, request: Request) -> Response:
    """Serve the agent card JSON schema.

    This endpoint provides W3C-compliant agent discovery information.
    """
    client_ip = get_client_ip(request)

    # Lazy initialization of agent card schema
    if app._agent_card_json_schema is None:
        logger.debug("Generating agent card schema")
        agent_card = create_agent_card(app)
        app._agent_card_json_schema = agent_card_ta.dump_json(agent_card, by_alias=True)

    logger.debug(f"Serving agent card to {client_ip}")
    return create_response_with_x402(
        request,
        app._agent_card_json_schema,
        response_type=Response,
        media_type="application/json",
    )
