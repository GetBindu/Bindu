"""Skills endpoints for detailed skill documentation and discovery.

These endpoints provide rich skill metadata for orchestrators to make
intelligent agent selection and routing decisions.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import SkillNotFoundError
from bindu.server.applications import BinduApplication
from bindu.utils.logging import get_logger
from .utils import (
    create_response_with_x402,
    extract_error_fields,
    get_client_ip,
    get_skill_or_error,
    handle_endpoint_errors,
    jsonrpc_error,
    validate_manifest,
)

logger = get_logger("bindu.server.endpoints.skills")


@handle_endpoint_errors("skills list")
async def skills_list_endpoint(app: BinduApplication, request: Request) -> Response:
    """List all skills available on this agent.

    Returns a summary of all skills with basic metadata for discovery.
    """
    client_ip = get_client_ip(request)
    logger.debug(f"Serving skills list to {client_ip}")

    # Ensure manifest exists
    error_resp = validate_manifest(app)
    if error_resp:
        return error_resp

    # Get skills from manifest
    skills = app.manifest.skills or []

    # Build summary response
    skills_summary = []
    for skill in skills:
        skill_summary = {
            "id": skill.get("id"),
            "name": skill.get("name"),
            "description": skill.get("description"),
            "version": skill.get("version", "unknown"),
            "tags": skill.get("tags", []),
            "input_modes": skill.get("input_modes", []),
            "output_modes": skill.get("output_modes", []),
        }

        # Add optional fields if present
        if "examples" in skill:
            skill_summary["examples"] = skill["examples"]

        if "documentation_path" in skill:
            skill_summary["documentation_path"] = skill["documentation_path"]

        skills_summary.append(skill_summary)

    response_data = {"skills": skills_summary, "total": len(skills_summary)}

    return create_response_with_x402(request, response_data)


@handle_endpoint_errors("skill detail")
async def skill_detail_endpoint(app: BinduApplication, request: Request) -> Response:
    """Get detailed information about a specific skill.

    Returns full skill metadata including documentation, capabilities,
    requirements, and performance characteristics.
    """
    client_ip = get_client_ip(request)
    skill_id = request.path_params.get("skill_id")

    if not skill_id:
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, "Skill ID not provided", status=404)

    logger.debug(f"Serving skill detail for '{skill_id}' to {client_ip}")

    # Ensure manifest exists
    error_resp = validate_manifest(
        app, client_ip, use_jsonrpc=True, error_type=SkillNotFoundError
    )
    if error_resp:
        return error_resp

    # Find skill in manifest
    skill, error_resp = get_skill_or_error(app, skill_id)
    if error_resp:
        return error_resp

    # Return full skill data (excluding documentation_content for size)
    skill_detail = dict(skill) if skill else {}

    # Remove documentation_content from response (too large)
    # Clients should use /agent/skills/{skill_id}/documentation for that
    if "documentation_content" in skill_detail:
        skill_detail["has_documentation"] = True
        del skill_detail["documentation_content"]
    else:
        skill_detail["has_documentation"] = False

    return create_response_with_x402(request, skill_detail)


@handle_endpoint_errors("skill documentation")
async def skill_documentation_endpoint(
    app: BinduApplication, request: Request
) -> Response:
    """Get the full skill.yaml documentation for a specific skill.

    Returns the complete YAML documentation that orchestrators can use
    to understand when and how to use this skill.
    """
    client_ip = get_client_ip(request)
    skill_id = request.path_params.get("skill_id")

    if not skill_id:
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, "Skill ID not provided", status=404)

    logger.debug(f"Serving skill documentation for '{skill_id}' to {client_ip}")

    # Ensure manifest exists
    error_resp = validate_manifest(
        app, client_ip, use_jsonrpc=True, error_type=SkillNotFoundError
    )
    if error_resp:
        return error_resp

    # Find skill in manifest
    skill, error_resp = get_skill_or_error(app, skill_id)
    if error_resp:
        return error_resp

    # Get documentation content
    documentation = skill.get("documentation_content")

    if not documentation:
        logger.warning(f"No documentation available for skill: {skill_id}")
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(
            code, f"No documentation available for skill: {skill_id}", status=404
        )

    # Return as YAML
    return create_response_with_x402(
        request, documentation, response_type=Response, media_type="application/yaml"
    )
